"""
video_service.py — Cut highlight clips and convert to 9:16 vertical WITHOUT cropping.

Instead of cropping (which cuts left/right content), we use FFmpeg's
scale+pad (letterbox) approach:
  - The full original video is scaled DOWN to fit inside 1080×1920
  - Black bars are added on top/bottom (or left/right) to fill the rest
  - No content is ever cut off

This means the speaker and all on-screen content remain fully visible.
"""

import cv2
import subprocess
import os
import sys
from moviepy import VideoFileClip, vfx

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ── Tool detection ────────────────────────────────────────

def is_ffmpeg_available() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except Exception:
        return False


# ── Video dimensions ──────────────────────────────────────

def get_video_dimensions(path: str):
    """Return (width, height) via ffprobe, fallback to (1920, 1080)."""
    try:
        out = subprocess.check_output(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "csv=p=0",
                path,
            ],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        w, h = map(int, out.split(","))
        return w, h
    except Exception:
        return 1920, 1080


# ── FFmpeg helpers ────────────────────────────────────────

def cut_clip_ffmpeg(video_path, start, end, output_path) -> bool:
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-i", video_path,
        "-to", str(end - start),
        "-c:v", "libx264",
        "-c:a", "aac",
        "-preset", "fast",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        print(f"⚠️ FFmpeg cut error:\n{result.stderr.decode(errors='replace')[-400:]}")
        return False
    return True


def letterbox_vertical_ffmpeg(input_path: str, output_path: str) -> str:
    """
    Convert any video to 1080×1920 (9:16) using letterboxing.

    FFmpeg filter breakdown:
      scale=1080:1920:force_original_aspect_ratio=decrease
        → scale the video DOWN so it fits inside 1080×1920, keeping aspect ratio
      pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black
        → pad with black bars on all sides to reach exactly 1080×1920

    Result: the entire original frame is visible, centred, with black bars
    on whichever axis has leftover space (top/bottom for landscape input,
    left/right for portrait input that is narrower than 1080).
    """
    w, h = get_video_dimensions(input_path)
    print(f"   Letterbox: src={w}×{h} → 1080×1920 (full frame preserved)")

    vf = (
        "scale=1080:1920:force_original_aspect_ratio=decrease,"
        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", vf,
        "-c:v", "libx264",
        "-c:a", "aac",
        "-preset", "fast",
        "-crf", "23",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        print(f"⚠️ FFmpeg letterbox error:\n{result.stderr.decode(errors='replace')[-400:]}")
        return input_path   # return original on failure
    return output_path


# ── MoviePy helpers ───────────────────────────────────────

def cut_clip_moviepy(video_path, start, end, output_path) -> bool:
    try:
        video = VideoFileClip(video_path)
        clip  = video.subclipped(start, end)
        clip.write_videofile(output_path, codec="libx264", audio_codec="aac", logger=None)
        video.close()
        clip.close()
        return True
    except Exception as e:
        print(f"⚠️ MoviePy cut error: {e}")
        return False


def letterbox_vertical_moviepy(input_path: str, output_path: str) -> str:
    """
    MoviePy fallback: resize to fit inside 1080×1920 keeping aspect ratio,
    then pad with black bars. No cropping — all content visible.
    """
    try:
        clip = VideoFileClip(input_path)
        src_w, src_h = clip.size

        # Scale to fit inside 1080×1920
        scale = min(1080 / src_w, 1920 / src_h)
        new_w = int(src_w * scale)
        new_h = int(src_h * scale)

        # Ensure even dimensions (required by libx264)
        new_w = new_w if new_w % 2 == 0 else new_w - 1
        new_h = new_h if new_h % 2 == 0 else new_h - 1

        resized = clip.resized((new_w, new_h))

        # Pad to 1080×1920 with black bars
        pad_x = (1080 - new_w) // 2
        pad_y = (1920 - new_h) // 2

        padded = resized.with_effects([
            vfx.Margin(
                left=pad_x, right=(1080 - new_w - pad_x),
                top=pad_y,  bottom=(1920 - new_h - pad_y),
                color=(0, 0, 0),
            )
        ])

        print(f"   Letterbox(MP): src={src_w}×{src_h} → scaled={new_w}×{new_h} → 1080×1920")

        padded.write_videofile(output_path, codec="libx264", audio_codec="aac", logger=None)
        clip.close()
        return output_path
    except Exception as e:
        print(f"⚠️ MoviePy letterbox error: {e}")
        return input_path


# ── Main entry point ──────────────────────────────────────

def create_clips(video_path: str, highlights: list) -> list:
    clips      = []
    use_ffmpeg = is_ffmpeg_available()
    print(f"🔧 Video tool: {'FFmpeg' if use_ffmpeg else 'MoviePy'}")

    # Get source duration so we never exceed it
    try:
        video          = VideoFileClip(video_path)
        video_duration = video.duration
        video.close()
    except Exception:
        video_duration = 9999

    for i, h in enumerate(highlights):
        start = float(h["start"])
        end   = float(h["end"])

        # Clamp to video length
        end = min(end, video_duration)

        # Enforce minimum 15 s, maximum 90 s clip length
        if end - start < 15:
            end = min(start + 60, video_duration)
        if end - start > 90:
            end = start + 90
        if end <= start:
            print(f"⚠️ Skipping clip {i} — invalid timestamps ({start}→{end})")
            continue

        print(f"\n✂️  Clip {i}: {start:.1f}s → {end:.1f}s  ({end-start:.0f}s)")

        raw_path      = os.path.join(OUTPUT_DIR, f"raw_clip_{i}.mp4")
        vertical_path = os.path.join(OUTPUT_DIR, f"vertical_clip_{i}.mp4")

        # ── Cut ──
        if use_ffmpeg:
            success = cut_clip_ffmpeg(video_path, start, end, raw_path)
        else:
            success = cut_clip_moviepy(video_path, start, end, raw_path)

        if not success or not os.path.exists(raw_path):
            print(f"❌ Clip {i} cut failed, skipping")
            continue

        # ── Letterbox to vertical (no cropping, full frame visible) ──
        if use_ffmpeg:
            result_path = letterbox_vertical_ffmpeg(raw_path, vertical_path)
        else:
            result_path = letterbox_vertical_moviepy(raw_path, vertical_path)

        clips.append({
            "path":   result_path,
            "hook":   h.get("hook",   "Watch this moment"),
            "reason": h.get("reason", "High impact moment"),
        })

        # Remove the raw clip to save space
        if os.path.exists(raw_path) and raw_path != result_path:
            try:
                os.remove(raw_path)
            except OSError:
                pass

    return clips