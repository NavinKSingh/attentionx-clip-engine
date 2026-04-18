"""
transcription_service.py — Transcribe a video file to timed text segments using Whisper.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import WHISPER_MODEL

import whisper

# Load model once at import time (expensive operation)
print(f"🔄 Loading Whisper model: {WHISPER_MODEL}…")
try:
    _model = whisper.load_model(WHISPER_MODEL)
    print(f"✅ Whisper '{WHISPER_MODEL}' model loaded")
except Exception as e:
    print(f"❌ Failed to load Whisper model '{WHISPER_MODEL}': {e}")
    _model = None


def transcribe_video(video_path: str) -> list:
    """
    Transcribe `video_path` and return a list of segment dicts:
      [{"start": float, "end": float, "text": str}, ...]

    Returns an empty list on failure.
    """
    if _model is None:
        print("❌ Whisper model not loaded — cannot transcribe")
        return []

    if not os.path.exists(video_path):
        print(f"❌ Video file not found: {video_path}")
        return []

    print(f"🎙️ Transcribing: {video_path}")

    try:
        result = _model.transcribe(video_path, language="en", word_timestamps=True)
    except Exception as e:
        print(f"❌ Whisper transcription error: {e}")
        return []

    # ── Preferred: use segment-level timestamps ──
    raw_segments = result.get("segments", [])
    if raw_segments:
        segments = []
        for seg in raw_segments:
            text = seg.get("text", "").strip()
            if not text:
                continue
            segments.append({
                "start": round(float(seg["start"]), 2),
                "end": round(float(seg["end"]), 2),
                "text": text,
            })
        if segments:
            print(f"✅ Transcribed {len(segments)} segment(s)")
            return segments

    # ── Fallback: full-text with a single dummy segment ──
    full_text = result.get("text", "").strip()
    if full_text:
        print("⚠️ No segments found — using full-text fallback")
        return [{"start": 0.0, "end": 10.0, "text": full_text}]

    print("⚠️ Transcription returned no usable text")
    return []