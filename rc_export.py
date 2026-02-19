# OTIO metadata conventions:
#   All rough-cut data lives under the "rough-cut" namespace.
#   Timeline metadata:  {"rough-cut": {"source_video", "video_duration", "fps"}}
#   Clip metadata:      {"rough-cut": {"transcript", "transcript_indices"}}
#   Marker metadata:    {"rough-cut": {"type": "take"|"broll", ...}}
#   Marker colors:      RED = take, GREEN = broll
#   Post-roll frames are baked into clip source_range duration at rough-cut time.

from pathlib import Path
from urllib.parse import quote

import opentimelineio as otio


def sanitize_name(text, max_length=40):
    """Clean text for FCPXML name attributes"""
    if not text:
        return ""
    text = text.replace('"', "'").replace('<', '').replace('>', '')
    text = text.replace('&', 'and').replace('/', '-')
    return text[:max_length].strip()


def sanitize_note(text, max_length=60):
    """Clean text for marker note attributes"""
    if not text:
        return ""
    text = text.replace('"', "'").replace('<', '').replace('>', '')
    text = text.replace('&', 'and').replace('\n', ' ')
    return text[:max_length].strip()


def seconds_to_frames(seconds, fps=30):
    """Convert seconds to frame count"""
    return int(seconds * fps)


def generate_fcpxml_from_otio(timeline, width=2560, height=1440):
    """Generate FCPXML string from an OTIO timeline"""

    rc_meta = timeline.metadata.get("rough-cut", {})
    video_path = rc_meta.get("source_video", "")
    video_duration = rc_meta.get("video_duration", 0)
    fps = rc_meta.get("fps", 30)

    video_name = Path(video_path).stem
    encoded_path = quote(str(video_path), safe='/:')
    duration_ms = int(video_duration * 1000)

    track = timeline.tracks[0]

    clips_xml = []
    timeline_offset = 0
    used_take_markers = set()

    for clip in track:
        if not isinstance(clip, otio.schema.Clip):
            continue

        sr = clip.source_range
        start_frames = int(sr.start_time.value)
        duration_frames = int(sr.duration.value)

        clip_name = sanitize_name(clip.name) or "Clip"

        markers = ""
        for marker in clip.markers:
            rc_marker = marker.metadata.get("rough-cut", {})
            marker_type = rc_marker.get("type", "")

            if marker_type == "take":
                removed_count = rc_marker.get("removed_count", 0)
                sample_text = rc_marker.get("sample_text", "")
                if sample_text not in used_take_markers:
                    used_take_markers.add(sample_text)
                    note = sanitize_note(sample_text)
                    markers += f'\n                            <marker start="{start_frames}/{fps}s" duration="100/3000s" value="{removed_count} takes removed" completed="0" note="{note}"/>'
            elif marker_type == "broll":
                noun = rc_marker.get("noun", "")
                markers += f'\n                            <marker start="{start_frames}/{fps}s" duration="100/3000s" value="B-roll: {noun}"/>'

        clip_xml = f'''                        <asset-clip ref="r2" offset="{timeline_offset}/{fps}s" name="{clip_name}" start="{start_frames}/{fps}s" duration="{duration_frames}/{fps}s" tcFormat="NDF" audioRole="dialogue">{markers}
                        </asset-clip>'''
        clips_xml.append(clip_xml)
        timeline_offset += duration_frames

    fcpxml = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fcpxml>

<fcpxml version="1.13">
    <resources>
        <format id="r1" frameDuration="100/3000s" width="{width}" height="{height}" colorSpace="1-1-1 (Rec. 709)"/>
        <asset id="r2" name="{video_name}" start="0s" duration="{duration_ms}00/1000s" hasVideo="1" format="r1" hasAudio="1" videoSources="1" audioSources="1" audioChannels="2" audioRate="48000">
            <media-rep kind="original-media" src="file://{encoded_path}"/>
        </asset>
    </resources>

    <library location="file:///Users/chan/Movies/Untitled.fcpbundle/">
        <event name="Rough Cut">
            <project name="Rough Cut">
                <sequence format="r1" duration="{timeline_offset}/{fps}s" tcStart="0s" tcFormat="NDF" audioLayout="stereo" audioRate="48k">
                    <spine>
{chr(10).join(clips_xml)}
                    </spine>
                </sequence>
            </project>
        </event>
    </library>
</fcpxml>
'''
    return fcpxml, timeline_offset


def generate_ffmpeg_filter(timeline):
    """Generate ffmpeg filter_complex script from OTIO timeline"""

    track = timeline.tracks[0]

    filter_parts = []
    concat_inputs = []
    clip_idx = 0

    for item in track:
        if not isinstance(item, otio.schema.Clip):
            continue

        sr = item.source_range
        start = sr.start_time.value / sr.start_time.rate
        end = start + sr.duration.value / sr.duration.rate

        filter_parts.append(
            f'[0:v]trim=start={start:.6f}:end={end:.6f},setpts=PTS-STARTPTS[v{clip_idx}]'
        )
        filter_parts.append(
            f'[0:a]atrim=start={start:.6f}:end={end:.6f},asetpts=PTS-STARTPTS[a{clip_idx}]'
        )
        concat_inputs.append(f'[v{clip_idx}][a{clip_idx}]')
        clip_idx += 1

    n = len(concat_inputs)
    filter_script = ';\n'.join(filter_parts)
    filter_script += f';\n{"".join(concat_inputs)}concat=n={n}:v=1:a=1[outv][outa]'

    return filter_script
