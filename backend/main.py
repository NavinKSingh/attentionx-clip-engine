"""
main.py — AttentionX FastAPI backend.

Architecture: job-based processing
  POST /upload/ or /upload_youtube/  →  returns {job_id} immediately (no timeout risk)
  GET  /status/{job_id}              →  frontend polls this every 3s
  GET  /clip/{filename}              →  serves generated clips
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

import shutil, os, sys, uuid, glob, threading
import yt_dlp
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.transcription_service import transcribe_video
from services.emotion_service import detect_highlights
from services.video_service import create_clips
from services.caption_service import generate_captions

# ── App setup ─────────────────────────────────────────────
app = FastAPI(
    title="AttentionX API",
    description="Automated Content Repurposing Engine",
    version="3.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

FRONTEND_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend"
)

app.mount("/clip", StaticFiles(directory=OUTPUT_DIR), name="clips")

# Dedicated thread pool — keeps pipeline off the main event loop
_executor = ThreadPoolExecutor(max_workers=2)

# ── In-memory job store ───────────────────────────────────
_jobs: dict = {}
_lock = threading.Lock()

STEP_LABELS = {
    "download":   "Downloading YouTube video",
    "transcribe": "Transcribing audio with Whisper",
    "highlights": "Analyzing highlights with Groq AI",
    "clips":      "Cutting & smart-cropping to 9:16",
    "captions":   "Burning captions on clips",
    "done":       "Finalizing viral clips",
}

# Ordered steps (download only shown for YouTube)
ALL_STEPS   = ["download", "transcribe", "highlights", "clips", "captions", "done"]
FILE_STEPS  = ["transcribe", "highlights", "clips", "captions", "done"]


def _progress(step: str, steps: list) -> int:
    """Map a step name to a 5-100 integer progress value."""
    if step not in steps:
        return 5
    idx = steps.index(step)
    return max(5, round(((idx + 0.5) / len(steps)) * 100))


def _set(job_id: str, **kw):
    with _lock:
        _jobs.setdefault(job_id, {}).update(kw)


def _get(job_id: str) -> Optional[dict]:
    with _lock:
        return dict(_jobs.get(job_id, {}))


# ── Helpers ───────────────────────────────────────────────
def cleanup_old_outputs():
    for pattern in [f"{OUTPUT_DIR}/{t}_clip_*.mp4" for t in ("raw","vertical","final")]:
        for f in glob.glob(pattern):
            try: os.remove(f)
            except OSError: pass


def build_clip_url(c: dict) -> dict:
    return {
        "clip_url": f"/clip/{os.path.basename(c.get('clip',''))}",
        "caption":  c.get("caption", ""),
        "reason":   c.get("reason", ""),
    }


# ── Pipeline thread ───────────────────────────────────────
def _run_pipeline(job_id: str, file_path: str, steps: list):
    try:
        cleanup_old_outputs()

        # 1 — Transcribe
        _set(job_id, step="transcribe", label=STEP_LABELS["transcribe"],
             progress=_progress("transcribe", steps))
        transcript = transcribe_video(file_path)
        if not transcript:
            raise ValueError("Transcription failed or returned empty segments")
        print(f"✅ Transcription done — {len(transcript)} segments")

        # 2 — Highlights
        _set(job_id, step="highlights", label=STEP_LABELS["highlights"],
             progress=_progress("highlights", steps))
        highlights = detect_highlights(transcript)
        if not highlights:
            raise ValueError("No highlights detected in the video")
        print(f"✅ Highlights — {len(highlights)} moments")

        # 3 — Clips
        _set(job_id, step="clips", label=STEP_LABELS["clips"],
             progress=_progress("clips", steps))
        clips = create_clips(file_path, highlights)
        if not clips:
            raise ValueError("Clip creation failed — no clips produced")
        print(f"✅ Clips created — {len(clips)}")

        # 4 — Captions
        _set(job_id, step="captions", label=STEP_LABELS["captions"],
             progress=_progress("captions", steps))
        final_outputs = generate_captions(clips)
        print(f"✅ Captions burned — {len(final_outputs)} clips ready")

        # 5 — Done
        _set(job_id,
             status="done", step="done", progress=100,
             label=STEP_LABELS["done"],
             result={
                 "status": "success",
                 "clips_generated": len(final_outputs),
                 "outputs": [build_clip_url(c) for c in final_outputs],
             },
             error=None)

    except Exception as e:
        print(f"❌ Pipeline error [{job_id}]: {e}")
        _set(job_id, status="error", error=str(e), progress=0)

    finally:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError:
            pass


def _download_then_run(job_id: str, url: str, output_path: str):
    """Download YouTube video, then kick off the pipeline — all in one thread."""
    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": output_path,
        "merge_output_format": "mp4",
        "overwrites": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print(f"✅ YouTube downloaded → {os.path.basename(output_path)}")
    except Exception as e:
        _set(job_id, status="error",
             error=f"YouTube download failed: {e}", progress=0)
        return

    if not os.path.exists(output_path):
        _set(job_id, status="error",
             error="Download appeared to succeed but file not found", progress=0)
        return

    _run_pipeline(job_id, output_path, ALL_STEPS)


# ── Frontend ──────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(path):
        return HTMLResponse(content=open(path, encoding="utf-8").read())
    return HTMLResponse("<h1>Frontend not found</h1>", status_code=404)


# ── Status polling endpoint ───────────────────────────────
@app.get("/status/{job_id}")
def get_status(job_id: str):
    job = _get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# ── Upload local file ─────────────────────────────────────
@app.post("/upload/")
async def upload_video(file: UploadFile = File(...)):
    allowed = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(400, f"Unsupported format: {ext}")

    file_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}{ext}")
    with open(file_path, "wb") as buf:
        shutil.copyfileobj(file.file, buf)
    print(f"📁 Saved: {os.path.basename(file_path)}")

    job_id = uuid.uuid4().hex
    _set(job_id, status="running", step="transcribe",
         progress=5, label=STEP_LABELS["transcribe"],
         result=None, error=None)

    _executor.submit(_run_pipeline, job_id, file_path, FILE_STEPS)
    return {"job_id": job_id}


# ── Upload YouTube URL ────────────────────────────────────
class YouTubeRequest(BaseModel):
    url: str


@app.post("/upload_youtube/")
async def upload_youtube(req: YouTubeRequest):
    output_path = os.path.join(UPLOAD_DIR, f"yt_{uuid.uuid4().hex}.mp4")

    job_id = uuid.uuid4().hex
    _set(job_id, status="running", step="download",
         progress=5, label=STEP_LABELS["download"],
         result=None, error=None)

    _executor.submit(_download_then_run, job_id, req.url, output_path)
    return {"job_id": job_id}


# ── Health ────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "healthy", "service": "AttentionX", "version": "3.0"}