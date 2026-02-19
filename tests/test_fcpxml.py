import unittest
import xml.etree.ElementTree as ET

from rc_fcpxml import (
    sanitize_name, sanitize_note, detect_proper_nouns,
    seconds_to_frames, get_transcript_for_segment, generate_fcpxml,
)


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


class TestDetectProperNouns(unittest.TestCase):

    def test_multiword_phrases(self):
        text = "I use Claude Code and Final Cut Pro for editing."
        result = detect_proper_nouns(text)
        self.assertIn("Claude Code", result)
        self.assertIn("Final Cut Pro", result)

    def test_filters_short_words(self):
        text = "Let me show you Cod and Mac tools."
        result = detect_proper_nouns(text)
        self.assertNotIn("Cod", result)
        self.assertNotIn("Mac", result)

    def test_filters_sentence_initial(self):
        text = "Let me show you Python. Now we can code."
        result = detect_proper_nouns(text)
        self.assertNotIn("Let", result)
        self.assertNotIn("Now", result)
        self.assertIn("Python", result)

    def test_empty_input(self):
        self.assertEqual(detect_proper_nouns(""), [])


class TestSecondsToFrames(unittest.TestCase):

    def test_30fps(self):
        self.assertEqual(seconds_to_frames(1.0, fps=30), 30)
        self.assertEqual(seconds_to_frames(0.5, fps=30), 15)

    def test_zero(self):
        self.assertEqual(seconds_to_frames(0.0), 0)


class TestGetTranscriptForSegment(unittest.TestCase):

    def test_overlapping_segments(self):
        transcript = [
            {"offsets": {"from": 0, "to": 2000}, "text": "First part"},
            {"offsets": {"from": 2000, "to": 4000}, "text": "Second part"},
            {"offsets": {"from": 4000, "to": 6000}, "text": "Third part"},
        ]
        text, indices = get_transcript_for_segment(transcript, 1.0, 3.0)
        self.assertIn("First part", text)
        self.assertIn("Second part", text)
        self.assertNotIn("Third part", text)
        self.assertEqual(indices, [0, 1])

    def test_no_overlap(self):
        transcript = [
            {"offsets": {"from": 0, "to": 1000}, "text": "Before"},
            {"offsets": {"from": 5000, "to": 6000}, "text": "After"},
        ]
        text, indices = get_transcript_for_segment(transcript, 2.0, 4.0)
        self.assertEqual(text, "")
        self.assertEqual(indices, [])


class TestGenerateFcpxml(unittest.TestCase):

    def test_generates_valid_xml(self):
        intervals = [{'start': 0, 'end': 2, 'duration': 2, 'text': 'Test content'}]
        markers = {}

        fcpxml, timeline_frames = generate_fcpxml(
            intervals, markers, "test.mp4", 2.0, width=1920, height=1080
        )

        root = ET.fromstring(fcpxml)
        self.assertEqual(root.tag, 'fcpxml')
        self.assertEqual(root.get('version'), '1.13')

    def test_has_required_structure(self):
        intervals = [{'start': 0, 'end': 2, 'duration': 2, 'text': 'Test'}]
        markers = {}

        fcpxml, _ = generate_fcpxml(intervals, markers, "test.mp4", 2.0)

        root = ET.fromstring(fcpxml)
        self.assertIsNotNone(root.find('.//resources'))
        self.assertIsNotNone(root.find('.//library'))
        self.assertIsNotNone(root.find('.//sequence'))
        self.assertIsNotNone(root.find('.//spine'))

    def test_multiple_clips(self):
        intervals = [
            {'start': 0, 'end': 2, 'duration': 2, 'text': 'First clip'},
            {'start': 3, 'end': 5, 'duration': 2, 'text': 'Second clip'},
        ]
        markers = {}

        fcpxml, _ = generate_fcpxml(intervals, markers, "test.mp4", 5.0)

        root = ET.fromstring(fcpxml)
        clips = root.findall('.//asset-clip')
        self.assertEqual(len(clips), 2)

    def test_take_markers(self):
        intervals = [
            {'start': 0, 'end': 2, 'duration': 2, 'text': 'Final take'},
        ]
        markers = {0: {'removed_count': 2, 'sample_text': 'hello world'}}

        fcpxml, _ = generate_fcpxml(intervals, markers, "test.mp4", 2.0)

        root = ET.fromstring(fcpxml)
        marker_elems = root.findall('.//marker')
        self.assertTrue(any('takes removed' in m.get('value', '') for m in marker_elems))

    def test_empty_intervals(self):
        fcpxml, timeline_frames = generate_fcpxml([], {}, "test.mp4", 2.0)
        root = ET.fromstring(fcpxml)
        clips = root.findall('.//asset-clip')
        self.assertEqual(len(clips), 0)
        self.assertEqual(timeline_frames, 0)


if __name__ == '__main__':
    unittest.main()
