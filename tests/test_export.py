import unittest
import xml.etree.ElementTree as ET

import opentimelineio as otio

from rc_export import sanitize_name, sanitize_note, seconds_to_frames, generate_fcpxml_from_otio


def _make_timeline(intervals, take_markers=None, video_path="test.mp4", duration=10.0, fps=30):
    """Helper to build an OTIO timeline for testing"""
    take_markers = take_markers or {}

    timeline = otio.schema.Timeline(name="Test")
    timeline.metadata["rough-cut"] = {
        "source_video": video_path,
        "video_duration": duration,
        "fps": fps,
    }

    track = otio.schema.Track(name="Main", kind=otio.schema.TrackKind.Video)

    for i, interval in enumerate(intervals):
        media_ref = otio.schema.ExternalReference(
            target_url=f"file://{video_path}",
            available_range=otio.opentime.TimeRange(
                start_time=otio.opentime.RationalTime(0, fps),
                duration=otio.opentime.RationalTime(int(duration * fps), fps)
            )
        )

        start_frames = int(interval['start'] * fps)
        duration_frames = int(interval['duration'] * fps) + 2

        clip = otio.schema.Clip(
            name=interval.get('text', '').strip()[:40] or f"Clip {i+1}",
            media_reference=media_ref,
            source_range=otio.opentime.TimeRange(
                start_time=otio.opentime.RationalTime(start_frames, fps),
                duration=otio.opentime.RationalTime(duration_frames, fps)
            ),
            metadata={
                "rough-cut": {
                    "transcript": interval.get('text', ''),
                }
            }
        )

        if i in take_markers:
            info = take_markers[i]
            marker = otio.schema.Marker(
                name=f"{info['removed_count']} takes removed",
                marked_range=otio.opentime.TimeRange(
                    start_time=otio.opentime.RationalTime(0, fps),
                    duration=otio.opentime.RationalTime(1, fps)
                ),
                color=otio.schema.MarkerColor.RED,
                metadata={
                    "rough-cut": {
                        "type": "take",
                        "removed_count": info['removed_count'],
                        "sample_text": info['sample_text'],
                    }
                }
            )
            clip.markers.append(marker)

        track.append(clip)

    timeline.tracks.append(track)
    return timeline


class TestSanitizeName(unittest.TestCase):

    def test_removes_slashes(self):
        self.assertEqual(sanitize_name("test/with/slash"), "test-with-slash")

    def test_truncates(self):
        result = sanitize_name("a" * 100, max_length=40)
        self.assertEqual(len(result), 40)

    def test_replaces_ampersand(self):
        self.assertEqual(sanitize_name("A & B"), "A and B")

    def test_empty_input(self):
        self.assertEqual(sanitize_name(""), "")
        self.assertEqual(sanitize_name(None), "")


class TestSanitizeNote(unittest.TestCase):

    def test_removes_newlines(self):
        result = sanitize_note("line1\nline2\nline3")
        self.assertNotIn("\n", result)

    def test_truncates(self):
        result = sanitize_note("a" * 100, max_length=60)
        self.assertEqual(len(result), 60)


class TestSecondsToFrames(unittest.TestCase):

    def test_30fps(self):
        self.assertEqual(seconds_to_frames(1.0, fps=30), 30)
        self.assertEqual(seconds_to_frames(0.5, fps=30), 15)

    def test_zero(self):
        self.assertEqual(seconds_to_frames(0.0), 0)


class TestGenerateFcpxmlFromOtio(unittest.TestCase):

    def test_generates_valid_xml(self):
        timeline = _make_timeline(
            [{'start': 0, 'end': 2, 'duration': 2, 'text': 'Test content'}],
            duration=2.0
        )

        fcpxml, _ = generate_fcpxml_from_otio(timeline, width=1920, height=1080)

        root = ET.fromstring(fcpxml)
        self.assertEqual(root.tag, 'fcpxml')
        self.assertEqual(root.get('version'), '1.13')

    def test_has_required_structure(self):
        timeline = _make_timeline(
            [{'start': 0, 'end': 2, 'duration': 2, 'text': 'Test'}],
            duration=2.0
        )

        fcpxml, _ = generate_fcpxml_from_otio(timeline)

        root = ET.fromstring(fcpxml)
        self.assertIsNotNone(root.find('.//resources'))
        self.assertIsNotNone(root.find('.//library'))
        self.assertIsNotNone(root.find('.//sequence'))
        self.assertIsNotNone(root.find('.//spine'))

    def test_multiple_clips(self):
        timeline = _make_timeline([
            {'start': 0, 'end': 2, 'duration': 2, 'text': 'First clip'},
            {'start': 3, 'end': 5, 'duration': 2, 'text': 'Second clip'},
        ], duration=5.0)

        fcpxml, _ = generate_fcpxml_from_otio(timeline)

        root = ET.fromstring(fcpxml)
        clips = root.findall('.//asset-clip')
        self.assertEqual(len(clips), 2)

    def test_take_markers(self):
        timeline = _make_timeline(
            [{'start': 0, 'end': 2, 'duration': 2, 'text': 'Final take'}],
            take_markers={0: {'removed_count': 2, 'sample_text': 'hello world'}},
            duration=2.0
        )

        fcpxml, _ = generate_fcpxml_from_otio(timeline)

        root = ET.fromstring(fcpxml)
        marker_elems = root.findall('.//marker')
        self.assertTrue(any('takes removed' in m.get('value', '') for m in marker_elems))

    def test_empty_timeline(self):
        timeline = _make_timeline([], duration=2.0)
        fcpxml, timeline_offset = generate_fcpxml_from_otio(timeline)
        root = ET.fromstring(fcpxml)
        clips = root.findall('.//asset-clip')
        self.assertEqual(len(clips), 0)
        self.assertEqual(timeline_offset, 0)


if __name__ == '__main__':
    unittest.main()
