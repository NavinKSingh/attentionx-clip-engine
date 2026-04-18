"""
caption_service.py — Burn a hook caption onto each vertical clip using FFmpeg.
"""

import subprocess
import os
import re
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ── Text sanitisation ─────────────────────────────────────

def sanitize_caption(text: str, max_chars: int = 50) -> str:
    """
    Produce a string safe to embed in an FFmpeg drawtext filter.
    - Strip non-ASCII characters
    - Remove characters that break the filter expression
    - Truncate to `max_chars`
    - Fall back to a default if nothing remains
    """
    # Keep only printable ASCII
    text = text.encode("ascii", "ignore").decode("ascii")
    # Remove characters ffmpeg drawtext can't handle
    for ch in ("'", '"', ":", "\\", "/", "[", "]", "{", "}", "=", "%"):
        text = text.replace(ch, "")
    text = re.sub(r'\s+', ' ', text).strip()
    text = text[:max_chars]
    return text if text else "Watch This Moment"


# ── Caption burning ───────────────────────────────────────

def burn_captions(video_path: str, caption_text: str, output_path: str) -> str:
    """
    Overlay `caption_text` near the bottom of `video_path` and write to `output_path`.
    Returns `output_path` on success, or `video_path` (original) on failure.
    """
    clean_text = sanitize_caption(caption_text)
    print(f"   Caption text: {clean_text!r}")

    drawtext_filter = (
        f"drawtext=text='{clean_text}':"
        "fontsize=52:"
        "fontcolor=white:"
        "borderw=4:"
        "bordercolor=black:"
        "x=(w-text_w)/2:"
        "y=h-160"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", drawtext_filter,
        "-c:v", "libx264",
        "-c:a", "copy",
        "-preset", "ultrafast",
        "-crf", "28",
        output_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=180)
        if result.returncode == 0 and os.path.exists(output_path):
            return output_path
        error_tail = result.stderr.decode(errors="replace")[-400:]
        print(f"⚠️ FFmpeg caption burn failed:\n{error_tail}")
    except subprocess.TimeoutExpired:
        print("⚠️ FFmpeg caption burn timed out")
    except Exception as e:
        print(f"⚠️ Caption burn error: {e}")

    # Return the un-captioned clip rather than nothing
    return video_path


# ── Public API ────────────────────────────────────────────

def generate_captions(clips: list) -> list:
    """
    Burn hook captions onto every clip in `clips`.

    Each item in `clips` must have:
      - "path"   : str — path to the vertical clip
      - "hook"   : str — caption text
      - "reason" : str — reason (passed through unchanged)

    Returns a list of dicts:
      [{"clip": str, "caption": str, "reason": str}, ...]
    """
    results = []

    for i, clip_info in enumerate(clips):
        video_path = clip_info.get("path", "")
        hook = clip_info.get("hook", "Watch This Moment")
        reason = clip_info.get("reason", "")

        if not video_path or not os.path.exists(video_path):
            print(f"⚠️ Clip {i} path missing or not found, skipping")
            continue

        print(f"📝 Burning caption on clip {i}: {hook[:40]!r}")

        final_path = os.path.join(OUTPUT_DIR, f"final_clip_{i}.mp4")
        result_path = burn_captions(video_path, hook, final_path)

        results.append({
            "clip": os.path.abspath(result_path),
            "caption": hook,
            "reason": reason,
        })

        # Clean up the intermediate vertical clip to save disk space
        if os.path.exists(video_path) and video_path != result_path:
            try:
                os.remove(video_path)
            except OSError:
                pass

    return results