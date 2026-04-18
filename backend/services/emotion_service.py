"""
emotion_service.py — Detect viral highlight moments from a transcript using Groq LLM.
Falls back to a simple text-length heuristic if all LLM calls fail.
"""

import json
import re
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GROQ_API_KEY

from groq import Groq

groq_client = Groq(api_key=GROQ_API_KEY)

PROMPT_TEMPLATE = """
You are an expert viral content analyst for social media (TikTok, Instagram Reels).

Analyze this video transcript and find the TOP 3 most impactful moments that would
perform well as short viral clips.

Look for:
- Surprising or counterintuitive insights
- Emotional or motivational moments
- Quotable one-liners
- High-energy or passionate speech
- Aha moment revelations

Transcript:
{transcript}

Return ONLY a valid JSON array (no markdown, no explanation) with exactly this format:
[
  {{
    "start": <start_time_in_seconds as float>,
    "end": <end_time_in_seconds as float>,
    "reason": "<why this moment is viral-worthy>",
    "hook": "<catchy 1-line caption for this clip>"
  }}
]

Rules:
- Each clip must be between 30 to 90 seconds long
- Pick genuinely impactful moments
- Make sure start and end times exist in the transcript
"""


# ── JSON parsing ──────────────────────────────────────────

def parse_highlights(raw_text: str) -> list:
    """Extract and validate a JSON highlight array from raw LLM output."""
    try:
        json_match = re.search(r'\[.*\]', raw_text, re.DOTALL)
        if json_match:
            highlights = json.loads(json_match.group())
            valid = []
            for h in highlights:
                try:
                    start = float(h.get("start", 0))
                    end = float(h.get("end", 0))
                    if end > start:
                        valid.append({
                            "start": start,
                            "end": end,
                            "reason": str(h.get("reason", "High impact moment")),
                            "hook": str(h.get("hook", "Watch this moment")),
                        })
                except (TypeError, ValueError):
                    continue
            return valid[:3]
    except Exception as e:
        print(f"⚠️ JSON parse error: {e}")
    return []


# ── Groq LLM call with model fallback ────────────────────

GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama3-70b-8192",
    "mixtral-8x7b-32768",
]


def try_groq(prompt: str) -> list:
    """Try each Groq model in order; return highlights on first success."""
    for model_name in GROQ_MODELS:
        try:
            print(f"🚀 Trying Groq model: {model_name}...")
            response = groq_client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000,
            )
            raw = response.choices[0].message.content.strip()
            highlights = parse_highlights(raw)
            if highlights:
                print(f"✅ Groq success with {model_name} — {len(highlights)} highlight(s)")
                return highlights
            else:
                print(f"⚠️ {model_name} returned no valid highlights, trying next…")
        except Exception as e:
            print(f"⚠️ {model_name} failed: {str(e)[:120]}")

    print("❌ All Groq models failed")
    return []


# ── Text-based fallback ───────────────────────────────────

def fallback_highlights(segments: list) -> list:
    """
    Simple heuristic fallback: pick the 3 longest / most content-rich segments
    and wrap each into a 60-second window.
    """
    print("📝 Using text-length fallback for highlight detection…")

    # Sort by text length descending, take top 3
    scored = sorted(segments, key=lambda s: len(s.get("text", "")), reverse=True)
    highlights = []

    for seg in scored:
        if len(seg.get("text", "")) < 30:
            continue
        start = float(seg["start"])
        end = min(float(seg["end"]), start + 60)
        if end - start < 5:
            end = start + 60

        # Avoid timestamp overlaps with already-chosen highlights
        overlap = any(
            not (end <= h["start"] or start >= h["end"])
            for h in highlights
        )
        if overlap:
            continue

        highlights.append({
            "start": start,
            "end": end,
            "reason": "High-content segment",
            "hook": "Must watch this moment",
        })

        if len(highlights) >= 3:
            break

    return highlights


# ── Public API ────────────────────────────────────────────

def detect_highlights(segments: list) -> list:
    """
    Main entry point.
    1. Builds a compact transcript string from the first 50 segments.
    2. Tries Groq LLM (with model fallback).
    3. Falls back to text-length heuristic if LLM unavailable.
    """
    if not segments:
        print("⚠️ detect_highlights received empty segment list")
        return []

    transcript_text = "\n".join(
        f"[{seg['start']}s - {seg['end']}s]: {seg['text']}"
        for seg in segments[:50]
    )

    prompt = PROMPT_TEMPLATE.format(transcript=transcript_text)

    highlights = try_groq(prompt)
    if highlights:
        return highlights

    return fallback_highlights(segments)