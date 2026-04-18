"""
file_handler.py — Utility helpers for safe file & directory operations.
Used across the AttentionX backend pipeline.
"""

import os
import glob
import shutil
import uuid


# ── Path helpers ──────────────────────────────────────────

def ensure_dir(path: str) -> str:
    """Create directory if it doesn't exist. Returns the path."""
    os.makedirs(path, exist_ok=True)
    return path


def unique_filename(directory: str, extension: str) -> str:
    """
    Generate a guaranteed-unique filename inside `directory`.
    Example: unique_filename("uploads", ".mp4") → "uploads/a3f9c1....mp4"
    """
    ensure_dir(directory)
    name = f"{uuid.uuid4().hex}{extension}"
    return os.path.join(directory, name)


def safe_remove(path: str) -> bool:
    """Delete a file without raising if it doesn't exist. Returns True if removed."""
    try:
        if path and os.path.exists(path):
            os.remove(path)
            return True
    except OSError as e:
        print(f"⚠️ Could not remove {path}: {e}")
    return False


def safe_copy(src: str, dst: str) -> bool:
    """Copy src → dst. Returns True on success."""
    try:
        shutil.copy2(src, dst)
        return True
    except Exception as e:
        print(f"⚠️ Copy failed {src} → {dst}: {e}")
        return False


# ── Cleanup helpers ───────────────────────────────────────

def cleanup_pattern(pattern: str) -> int:
    """Remove all files matching a glob pattern. Returns count removed."""
    removed = 0
    for f in glob.glob(pattern):
        if safe_remove(f):
            removed += 1
    return removed


def cleanup_output_dir(output_dir: str) -> int:
    """
    Remove all intermediate and final clip files from a previous pipeline run.
    Keeps the directory itself intact.
    """
    patterns = [
        os.path.join(output_dir, "raw_clip_*.mp4"),
        os.path.join(output_dir, "vertical_clip_*.mp4"),
        os.path.join(output_dir, "final_clip_*.mp4"),
    ]
    total = sum(cleanup_pattern(p) for p in patterns)
    if total:
        print(f"🧹 Cleaned {total} old clip(s) from {output_dir}")
    return total


def cleanup_upload(file_path: str) -> None:
    """
    Optionally delete an uploaded source file after processing.
    Call this at the end of the pipeline to free disk space.
    """
    if file_path and os.path.exists(file_path):
        safe_remove(file_path)
        print(f"🗑️  Removed source upload: {os.path.basename(file_path)}")


# ── Validation helpers ────────────────────────────────────

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


def is_valid_video(filename: str) -> bool:
    """Return True if the file extension is an allowed video format."""
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_VIDEO_EXTENSIONS


def get_extension(filename: str) -> str:
    """Return lowercase extension including the dot, e.g. '.mp4'."""
    return os.path.splitext(filename)[1].lower()


def file_size_mb(path: str) -> float:
    """Return file size in MB, or 0.0 if file doesn't exist."""
    try:
        return os.path.getsize(path) / (1024 * 1024)
    except OSError:
        return 0.0