import json
import logging
import subprocess
from pathlib import Path

from rc_common import RoughCutError, run_command

logger = logging.getLogger(__name__)


def extract_audio(video_path, output_path):
    """Extract audio from video as 16kHz mono WAV"""
    cmd = [
        'ffmpeg', '-i', str(video_path),
        '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
        str(output_path), '-y'
    ]
    run_command(cmd, "Extracting audio")


def transcribe_audio(audio_path, output_path):
    """Transcribe audio with whisper-cli"""
    whisper_model = Path.home() / '.whisper' / 'models' / 'ggml-large-v3-turbo.bin'

    if not whisper_model.exists():
        raise RoughCutError(f"Whisper model not found: {whisper_model}")

    cmd = [
        'whisper-cli',
        '-m', str(whisper_model),
        '-f', str(audio_path),
        '--output-json'
    ]

    run_command(cmd, "Transcribing audio")

    # Whisper creates {audio_name}.json next to the audio file
    audio_name = audio_path.name
    generated_json = audio_path.parent / f"{audio_name}.json"

    if not generated_json.exists():
        raise RoughCutError(f"Whisper did not create expected output: {generated_json}")

    if generated_json != output_path:
        generated_json.rename(output_path)


def load_transcript(json_path):
    """Load whisper transcript JSON"""
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        return data['transcription']
    except FileNotFoundError:
        raise RoughCutError(f"Transcript file not found: {json_path}")
    except json.JSONDecodeError:
        raise RoughCutError(f"Invalid JSON in transcript: {json_path}")
    except KeyError:
        raise RoughCutError("Transcript missing 'transcription' key")


def get_video_duration(video_path):
    """Get video duration in seconds using ffprobe"""
    cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        str(video_path)
    ]
    result = run_command(cmd, "Getting video duration", capture_output=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        raise RoughCutError(f"Could not parse video duration: {result.stdout}")


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
