import logging
import re

from rc_common import RoughCutError, run_command

logger = logging.getLogger(__name__)


def detect_silences(video_path, output_path, threshold_db=-45, min_duration=0.5):
    """Detect silences with ffmpeg silencedetect"""
    cmd = f'ffmpeg -i "{video_path}" -af silencedetect=n={threshold_db}dB:d={min_duration} -f null - 2>&1 | grep -E "silence_start|silence_end"'

    result = run_command(cmd, "Detecting silences", capture_output=True, check=False)

    with open(output_path, 'w') as f:
        f.write(result.stdout)

    silence_count = result.stdout.count('silence_start')
    logger.info(f"  Found {silence_count} silence intervals")


def load_silences(txt_path):
    """Parse ffmpeg silence detection output"""
    try:
        intervals = []
        current_start = None

        with open(txt_path, 'r') as f:
            for line in f:
                if 'silence_start' in line:
                    match = re.search(r'silence_start: ([\d.]+)', line)
                    if match:
                        current_start = float(match.group(1))
                elif 'silence_end' in line and current_start is not None:
                    match = re.search(r'silence_end: ([\d.]+)', line)
                    if match:
                        intervals.append({
                            'start': current_start,
                            'end': float(match.group(1))
                        })
                        current_start = None

        return intervals
    except FileNotFoundError:
        raise RoughCutError(f"Silence file not found: {txt_path}")


def invert_silences(silences, duration, min_speech=0.3):
    """Convert silence intervals to speech intervals (the gaps between silences)"""
    speech = []
    cursor = 0.0
    for s in silences:
        if s['start'] > cursor:
            dur = s['start'] - cursor
            if dur >= min_speech:
                speech.append({'start': cursor, 'end': s['start'], 'duration': dur})
        cursor = max(cursor, s['end'])
    if duration > cursor:
        dur = duration - cursor
        if dur >= min_speech:
            speech.append({'start': cursor, 'end': duration, 'duration': dur})
    return speech
