import re
from pathlib import Path
from urllib.parse import quote


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


def detect_proper_nouns(text):
    """Detect proper nouns for B-roll markers"""
    if not text:
        return []

    exclude = {'I', 'A', 'An', 'The', 'In', 'On', 'At', 'To', 'For', 'Of', 'And', 'Or', 'But',
               'My', 'Your', 'His', 'Her', 'Its', 'Our', 'Their', 'We', 'You', 'He', 'She', 'It',
               'They', 'What', 'When', 'Where', 'Why', 'How', 'This', 'That', 'These', 'Those',
               'Let', 'Now', 'So', 'Well', 'Just', 'Then', 'Here', 'There'}

    proper_nouns = set()
    multi_word_phrases = set()

    # Find multi-word capitalized phrases
    multi_word = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', text)
    for phrase in multi_word:
        proper_nouns.add(phrase)
        multi_word_phrases.add(phrase)

    # Find mid-sentence capitalized words
    sentences = re.split(r'[.!?]\s+', text)

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        words = sentence.split()

        for i in range(1, len(words)):
            word = words[i]
            match = re.match(r'^([A-Z][a-z]+)', word)
            if match:
                cap_word = match.group(1)
                if len(cap_word) < 4:
                    continue
                if cap_word not in exclude:
                    is_part_of_phrase = any(cap_word in phrase for phrase in multi_word_phrases)
                    if not is_part_of_phrase:
                        proper_nouns.add(cap_word)

    return sorted(proper_nouns)


def seconds_to_frames(seconds, fps=30):
    """Convert seconds to frame count"""
    return int(seconds * fps)


def get_transcript_for_segment(transcript, seg_start, seg_end):
    """Get transcript text for a time range by overlap"""
    texts = []
    indices = []
    for i, seg in enumerate(transcript):
        t_start = seg['offsets']['from'] / 1000
        t_end = seg['offsets']['to'] / 1000
        if t_start < seg_end and t_end > seg_start:
            texts.append(seg['text'].strip())
            indices.append(i)
    return ' '.join(texts), indices


def generate_fcpxml(intervals, take_markers, video_path, video_duration,
                    width=2560, height=1440, post_roll_frames=2, enable_broll=True):
    """Generate FCPXML string from speech intervals"""

    video_name = Path(video_path).stem
    encoded_path = quote(str(video_path), safe='/:')
    duration_ms = int(video_duration * 1000)

    clips_xml = []
    timeline_offset = 0
    used_take_markers = set()

    for i, seg in enumerate(intervals):
        start_frames = seconds_to_frames(seg['start'])
        duration_frames = seconds_to_frames(seg['duration']) + post_roll_frames

        text = seg.get('text', '')
        clip_name = sanitize_name(text[:50]) or f"Clip {i + 1}"

        markers = ""

        # Take markers
        if i in take_markers:
            info = take_markers[i]
            if info['removed_count'] > 0:
                marker_key = info['sample_text']
                if marker_key not in used_take_markers:
                    used_take_markers.add(marker_key)
                    sample = sanitize_note(info['sample_text'])
                    markers += f'\n                            <marker start="{start_frames}/30s" duration="100/3000s" value="{info["removed_count"]} takes removed" completed="0" note="{sample}"/>'

        # B-roll markers
        if enable_broll:
            proper_nouns = detect_proper_nouns(text)
            for noun in proper_nouns:
                markers += f'\n                            <marker start="{start_frames}/30s" duration="100/3000s" value="B-roll: {noun}"/>'

        clip_xml = f'''                        <asset-clip ref="r2" offset="{timeline_offset}/30s" name="{clip_name}" start="{start_frames}/30s" duration="{duration_frames}/30s" tcFormat="NDF" audioRole="dialogue">{markers}
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
                <sequence format="r1" duration="{timeline_offset}/30s" tcStart="0s" tcFormat="NDF" audioLayout="stereo" audioRate="48k">
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
