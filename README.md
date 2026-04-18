# ⚡ AttentionX — Automated Content Repurposing Engine

> **AttentionX AI Hackathon 2026 | UnsaidTalks**  
> Built by **Navin Kumar Singh**

---

## 🎥 Demo Video Presentation

> ### 👉 [CLICK HERE TO WATCH DEMO VIDEO](https://drive.google.com/file/d/1dn8hwf6T_73WUKvfwrgcawOHBtoxNnDl/view?usp=sharing)

---

## 📌 Problem Statement

Mentors, educators, and creators produce hours of high-value long-form video content — but modern audiences consume information in **60-second bursts**. Valuable "golden nuggets" of wisdom are buried inside 60-minute videos, making them inaccessible to the average viewer.

**Common challenges:**
- Manually sifting through hours of footage to find viral or high-impact moments
- Converting horizontal (16:9) video to vertical (9:16) without losing content
- Manually transcribing and timing captions to keep viewers engaged

---

## 💡 Solution — AttentionX

**AttentionX** is an AI-powered platform where users upload any long-form video and the app automatically:

- 🎯 **Identifies Emotional Peaks** — Detects the 3 most impactful, viral-worthy moments using Groq LLM sentiment analysis
- 📐 **Converts to Vertical Format** — Uses FFmpeg letterboxing to produce 9:16 clips with **zero content cropped**
- 📝 **Generates Dynamic Captions** — Burns AI-written hook captions directly onto each clip

> **One upload. Three viral clips. A week's worth of content — in under 5 minutes.**

---

## 🏗️ Project Structure

```
AttentionX/
├── backend/
│   ├── services/
│   │   ├── caption_service.py        # Burns hook captions using FFmpeg drawtext
│   │   ├── emotion_service.py        # Detects highlights via Groq LLM (Llama 3.3 70B)
│   │   ├── transcription_service.py  # Transcribes audio using OpenAI Whisper
│   │   └── video_service.py          # Cuts clips & letterboxes to 9:16 vertical
│   ├── utils/
│   │   └── file_handler.py           # File management utilities
│   ├── config.py                     # API keys and configuration
│   ├── main.py                       # FastAPI backend — job-based async processing
│   └── requirements.txt              # Python dependencies
├── frontend/
│   ├── app.py                        # Streamlit frontend (optional)
│   └── index.html                    # Main UI — real-time progress polling
└── README.md
```

---

## 🧠 How It Works

```
Upload Video / YouTube URL
         ↓
   OpenAI Whisper
   (Transcription with timestamps)
         ↓
   Groq Llama 3.3 70B
   (Identifies top 3 viral moments)
         ↓
   FFmpeg — Cut + Letterbox to 9:16
   (Full frame preserved, no cropping)
         ↓
   FFmpeg drawtext
   (AI hook captions burned onto clips)
         ↓
   3 Downloadable Viral Clips 
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Backend** | FastAPI (Python) | Async REST API with job-based processing |
| **Transcription** | OpenAI Whisper | High-accuracy audio-to-text with timestamps |
| **AI Highlights** | Groq — Llama 3.3 70B | Emotion & sentiment-based viral moment detection |
| **Video Processing** | FFmpeg | Clip cutting, letterbox cropping, caption burning |
| **Face Detection** | OpenCV (Haar Cascade) | Speaker tracking for smart crop centering |
| **YouTube Support** | yt-dlp | Direct YouTube URL downloading |
| **Frontend** | HTML / CSS / JS | Real-time polling UI with progress tracker |

---

## ✨ Key Features

- **Job-based async processing** — UI never freezes, real-time step-by-step progress
- **YouTube + file upload support** — paste any YouTube link or upload a local video
- **Groq model fallback** — tries Llama 3.3 70B → Llama3 70B → Mixtral automatically
- **FFmpeg letterboxing** — full video frame always visible, zero content cut off
- **Auto caption burning** — AI-written hook captions overlaid on every clip
- **Text-length fallback** — works even if LLM is unavailable

---

## 🚀 Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/your-username/attentionx.git
cd attentionx
```

### 2. Install dependencies
```bash
pip install -r backend/requirements.txt
```

### 3. Set up API keys in `backend/config.py`
```python
GROQ_API_KEY = "your_groq_api_key"
WHISPER_MODEL = "base"   # or "small", "medium" for better accuracy
```

### 4. Run the backend
```bash
cd backend
uvicorn main:app --reload --port 8000
```

### 5. Open the app
Visit `http://localhost:8000` in your browser.

---

## 📦 Requirements

```
fastapi
uvicorn
openai-whisper
groq
moviepy
opencv-python
ffmpeg-python
yt-dlp
python-multipart
pydantic
```

> **Note:** FFmpeg must be installed on your system separately.  
> Install: https://ffmpeg.org/download.html

---

## 📊 Evaluation Criteria Mapping

| Criteria | How AttentionX addresses it |
|---|---|
| **Impact (20%)** | Turns 1 hour of content into 3 viral clips automatically — real, measurable value |
| **Innovation (20%)** | Cuts by meaning (emotion/sentiment), not just time — unique AI-first approach |
| **Technical Execution (20%)** | Clean modular codebase, async jobs, multi-model fallback, robust error handling |
| **User Experience (25%)** | Real-time progress UI, drag-and-drop upload, YouTube support, instant download |
| **Presentation (15%)** | Demo video linked above with full working prototype walkthrough |

---

## 👨‍💻 Author

**Navin Kumar Singh**  
AttentionX AI Hackathon 2026 — UnsaidTalks

---

## 📄 License

This project was built for the **AttentionX AI Hackathon** organized by **UnsaidTalks Education**.  
For queries: info@unsaidtalks.com | +91-7303573374