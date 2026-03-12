"""
NeuralNautic Transcriptor - Backend
FastAPI Server: Transkription, Stille-Erkennung, Folien-Extraktion
"""

import os
import json
import uuid
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import imageio_ffmpeg
import cv2

# FFmpeg Pfad (imageio-ffmpeg Bundle — kein separates Install nötig)
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

# FFmpeg-Verzeichnis in PATH eintragen, damit Whisper es findet
_ffmpeg_dir = str(Path(FFMPEG).parent)
if _ffmpeg_dir not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

import numpy as np
import whisper
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from docx import Document
from docx.shared import Inches
import markdown

app = FastAPI(title="NeuralNautic Transcriptor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Arbeitsverzeichnis
WORK_DIR = Path("transcriptor_jobs")
WORK_DIR.mkdir(exist_ok=True)

# Jobs status speichern
jobs: dict = {}

# Whisper Modell (wird lazy geladen)
_whisper_model = None

def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = whisper.load_model("small")
    return _whisper_model


# ── Audio Extraktion ──────────────────────────────────────────────────────────

def extract_audio(video_path: Path, out_path: Path) -> bool:
    """Extrahiert Audio aus Video mit FFmpeg"""
    result = subprocess.run([
        FFMPEG, "-y", "-i", str(video_path),
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        str(out_path)
    ], capture_output=True, text=True)
    return result.returncode == 0


# ── Stille-Erkennung ─────────────────────────────────────────────────────────

def detect_silence(audio_path: Path, min_silence_sec: float = 2.0) -> list[dict]:
    """Findet Stille-Segmente via FFmpeg silencedetect"""
    result = subprocess.run([
        FFMPEG, "-i", str(audio_path),
        "-af", f"silencedetect=noise=-40dB:d={min_silence_sec}",
        "-f", "null", "-"
    ], capture_output=True, text=True)

    output = result.stderr
    silent_segments = []
    starts = []

    for line in output.split('\n'):
        if 'silence_start' in line:
            try:
                t = float(line.split('silence_start:')[1].strip())
                starts.append(t)
            except:
                pass
        elif 'silence_end' in line:
            try:
                parts = line.split('silence_end:')[1].strip().split('|')
                end = float(parts[0].strip())
                if starts:
                    start = starts.pop(0)
                    silent_segments.append({
                        "start": round(start, 2),
                        "end": round(end, 2),
                        "duration": round(end - start, 2)
                    })
            except:
                pass

    return silent_segments


# ── Folien-Extraktion ─────────────────────────────────────────────────────────

def extract_slides(video_path: Path, out_dir: Path, threshold: float = 0.93) -> list[dict]:
    """Erkennt Szenenänderungen und extrahiert Folien/Keyframes"""
    out_dir.mkdir(exist_ok=True)
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS)

    slides = []
    prev_frame = None
    frame_idx = 0
    slide_count = 0
    last_slide_time = -3.0  # Mindestabstand in Sekunden

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Nur jeden 15. Frame prüfen (Performance + weniger False Positives)
        if frame_idx % 15 == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, (160, 90))

            if prev_frame is not None:
                diff = cv2.absdiff(prev_frame, gray)
                score = 1.0 - (diff.mean() / 255.0)

                timestamp = frame_idx / fps
                if score < threshold and (timestamp - last_slide_time) >= 3.0:
                    # Szenenänderung erkannt → Frame speichern
                    filename = f"slide_{slide_count:04d}_{int(timestamp)}s.jpg"
                    filepath = out_dir / filename
                    cv2.imwrite(str(filepath), frame)
                    slides.append({
                        "timestamp": round(timestamp, 2),
                        "timestamp_fmt": _fmt_time(timestamp),
                        "file": filename,
                        "frame": frame_idx
                    })
                    slide_count += 1
                    last_slide_time = timestamp

            prev_frame = gray

        frame_idx += 1

    cap.release()

    # Ersten Frame immer hinzufügen
    cap2 = cv2.VideoCapture(str(video_path))
    ret, first_frame = cap2.read()
    if ret:
        filename = "slide_first_0s.jpg"
        cv2.imwrite(str(out_dir / filename), first_frame)
        slides.insert(0, {"timestamp": 0.0, "timestamp_fmt": "00:00", "file": filename, "frame": 0})
    cap2.release()

    return slides


def _fmt_time(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


# ── Transkription ─────────────────────────────────────────────────────────────

def transcribe_audio(audio_path: Path) -> dict:
    """Transkribiert Audio mit Whisper — lädt WAV direkt als numpy array (kein ffmpeg nötig)"""
    import wave, struct
    model = get_whisper_model()

    # WAV direkt einlesen → numpy array (umgeht Whispers internen ffmpeg-Aufruf)
    with wave.open(str(audio_path), 'rb') as wf:
        frames = wf.readframes(wf.getnframes())
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()

    if sampwidth == 2:
        audio_np = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    else:
        audio_np = np.frombuffer(frames, dtype=np.float32)

    # Mono
    if n_channels > 1:
        audio_np = audio_np.reshape(-1, n_channels).mean(axis=1)

    # Whisper erwartet 16kHz
    if framerate != 16000:
        import whisper.audio as wa
        audio_np = wa.resample(audio_np, framerate, 16000)

    result = model.transcribe(audio_np, language="de", verbose=False)
    return result


# ── Export-Funktionen ─────────────────────────────────────────────────────────

def build_transcript_data(whisper_result: dict, silence: list, slides: list) -> dict:
    """Kombiniert alle Daten zu einem strukturierten Transkript"""
    segments = []
    for seg in whisper_result.get("segments", []):
        segments.append({
            "start": round(seg["start"], 2),
            "end": round(seg["end"], 2),
            "start_fmt": _fmt_time(seg["start"]),
            "end_fmt": _fmt_time(seg["end"]),
            "text": seg["text"].strip(),
            "type": "speech"
        })

    # Stille-Segmente einmischen
    for s in silence:
        if s["duration"] >= 2.0:
            segments.append({
                "start": s["start"],
                "end": s["end"],
                "start_fmt": _fmt_time(s["start"]),
                "end_fmt": _fmt_time(s["end"]),
                "text": f"[Kein Ton – {s['duration']:.0f}s Stille]",
                "type": "silence"
            })

    segments.sort(key=lambda x: x["start"])

    # Zugehörige Folie für jedes Segment finden
    for seg in segments:
        seg["slide"] = None
        for slide in reversed(slides):
            if slide["timestamp"] <= seg["start"]:
                seg["slide"] = slide["file"]
                break

    return {
        "language": whisper_result.get("language", "unknown"),
        "segments": segments,
        "slides": slides,
        "silence": silence,
        "full_text": whisper_result.get("text", "").strip()
    }


def export_markdown(data: dict, out_path: Path):
    lines = [f"# Transkript\n\n**Sprache:** {data['language']}\n"]
    for seg in data["segments"]:
        if seg["type"] == "silence":
            lines.append(f"\n> ⚠️ `{seg['start_fmt']} – {seg['end_fmt']}` {seg['text']}\n")
        else:
            lines.append(f"\n**[{seg['start_fmt']}]** {seg['text']}")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def export_html(data: dict, out_path: Path, slides_dir: Path):
    segments_html = ""
    for seg in data["segments"]:
        slide_html = ""
        if seg.get("slide"):
            slide_html = f'<img src="slides/{seg["slide"]}" class="slide-thumb" alt="Folie">'

        if seg["type"] == "silence":
            segments_html += f"""
            <div class="segment silence">
                <span class="timestamp">{seg['start_fmt']} – {seg['end_fmt']}</span>
                <span class="silence-label">⚠ {seg['text']}</span>
            </div>"""
        else:
            segments_html += f"""
            <div class="segment speech">
                <span class="timestamp">[{seg['start_fmt']}]</span>
                <span class="text">{seg['text']}</span>
                {slide_html}
            </div>"""

    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<title>NeuralNautic Transkript</title>
<style>
  body {{ background: #001428; color: #f0f8ff; font-family: 'Segoe UI', sans-serif; padding: 2rem; }}
  h1 {{ color: #00ffff; text-shadow: 0 0 10px rgba(0,255,255,0.5); }}
  .segment {{ margin: 0.8rem 0; padding: 0.8rem; border-radius: 8px; display: flex; gap: 1rem; align-items: flex-start; }}
  .speech {{ background: rgba(0,20,40,0.8); border-left: 3px solid #00ffff; }}
  .silence {{ background: rgba(40,10,0,0.6); border-left: 3px solid #ffd700; }}
  .timestamp {{ color: #00cccc; font-size: 0.85rem; white-space: nowrap; min-width: 80px; }}
  .silence-label {{ color: #ffd700; font-style: italic; }}
  .slide-thumb {{ max-width: 200px; border-radius: 6px; border: 1px solid #00cccc44; }}
  .text {{ flex: 1; }}
</style>
</head>
<body>
<h1>NeuralNautic Transkript</h1>
<p style="color:#a0b4c8">Sprache: <strong style="color:#00ffff">{data['language']}</strong></p>
{segments_html}
</body>
</html>"""
    out_path.write_text(html, encoding="utf-8")


def export_pdf(data: dict, out_path: Path, slides_dir: Path):
    doc = SimpleDocTemplate(str(out_path), pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('title', parent=styles['Heading1'], fontSize=18)
    story.append(Paragraph("NeuralNautic Transkript", title_style))
    story.append(Spacer(1, 0.5 * cm))

    for seg in data["segments"]:
        if seg["type"] == "silence":
            p = Paragraph(f"<b>[{seg['start_fmt']}–{seg['end_fmt']}]</b> ⚠ {seg['text']}", styles['Italic'])
        else:
            p = Paragraph(f"<b>[{seg['start_fmt']}]</b> {seg['text']}", styles['Normal'])
        story.append(p)

        if seg.get("slide"):
            slide_path = slides_dir / seg["slide"]
            if slide_path.exists():
                try:
                    story.append(RLImage(str(slide_path), width=8 * cm, height=4.5 * cm))
                except:
                    pass
        story.append(Spacer(1, 0.2 * cm))

    doc.build(story)


def export_docx(data: dict, out_path: Path, slides_dir: Path):
    doc = Document()
    doc.add_heading("NeuralNautic Transkript", 0)
    doc.add_paragraph(f"Sprache: {data['language']}")

    for seg in data["segments"]:
        if seg["type"] == "silence":
            p = doc.add_paragraph()
            p.add_run(f"[{seg['start_fmt']}–{seg['end_fmt']}] ").bold = True
            p.add_run(seg["text"]).italic = True
        else:
            p = doc.add_paragraph()
            run = p.add_run(f"[{seg['start_fmt']}] ")
            run.bold = True
            p.add_run(seg["text"])

        if seg.get("slide"):
            slide_path = slides_dir / seg["slide"]
            if slide_path.exists():
                try:
                    doc.add_picture(str(slide_path), width=Inches(4))
                except:
                    pass

    doc.save(str(out_path))


# ── Background Job ─────────────────────────────────────────────────────────────

def run_job(job_id: str, video_path: Path):
    job_dir = WORK_DIR / job_id
    job_dir.mkdir(exist_ok=True)
    slides_dir = job_dir / "slides"

    try:
        def update(step: str, progress: int, msg: str = ""):
            jobs[job_id]["step"] = step
            jobs[job_id]["progress"] = progress
            jobs[job_id]["message"] = msg

        update("audio", 10, "Extrahiere Audio...")
        audio_path = job_dir / "audio.wav"
        if not extract_audio(video_path, audio_path):
            raise RuntimeError("FFmpeg Audio-Extraktion fehlgeschlagen")

        update("silence", 25, "Erkenne Stille-Segmente...")
        silence = detect_silence(audio_path)

        update("slides", 40, "Extrahiere Folien...")
        slides = extract_slides(video_path, slides_dir)

        update("transcribe", 60, f"Transkribiere... ({len(slides)} Folien gefunden)")
        whisper_result = transcribe_audio(audio_path)

        update("build", 85, "Erstelle Transkript...")
        transcript_data = build_transcript_data(whisper_result, silence, slides)

        # Alle Formate exportieren
        update("export", 90, "Exportiere...")
        export_markdown(transcript_data, job_dir / "transcript.md")
        export_html(transcript_data, job_dir / "transcript.html", slides_dir)
        export_pdf(transcript_data, job_dir / "transcript.pdf", slides_dir)
        export_docx(transcript_data, job_dir / "transcript.docx", slides_dir)

        # JSON für Frontend
        (job_dir / "transcript.json").write_text(
            json.dumps(transcript_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        jobs[job_id]["status"] = "done"
        jobs[job_id]["progress"] = 100
        jobs[job_id]["message"] = "Fertig!"
        jobs[job_id]["data"] = transcript_data

    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["message"] = str(e)


# ── API Routes ────────────────────────────────────────────────────────────────

@app.post("/upload")
async def upload_video(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())[:8]
    job_dir = WORK_DIR / job_id
    job_dir.mkdir(exist_ok=True)

    video_path = job_dir / file.filename
    with open(video_path, "wb") as f:
        content = await file.read()
        f.write(content)

    jobs[job_id] = {
        "id": job_id,
        "filename": file.filename,
        "status": "running",
        "step": "start",
        "progress": 0,
        "message": "Starte...",
        "data": None
    }

    background_tasks.add_task(run_job, job_id, video_path)
    return {"job_id": job_id}


@app.get("/status/{job_id}")
def get_status(job_id: str):
    if job_id not in jobs:
        return JSONResponse(status_code=404, content={"error": "Job nicht gefunden"})
    return jobs[job_id]


@app.get("/download/{job_id}/{format}")
def download(job_id: str, format: str):
    allowed = {"md", "html", "pdf", "docx"}
    if format not in allowed:
        return JSONResponse(status_code=400, content={"error": "Ungültiges Format"})
    path = WORK_DIR / job_id / f"transcript.{format}"
    if not path.exists():
        return JSONResponse(status_code=404, content={"error": "Datei nicht gefunden"})
    return FileResponse(str(path), filename=f"transcript.{format}")


@app.get("/slides/{job_id}/{filename}")
def get_slide(job_id: str, filename: str):
    path = WORK_DIR / job_id / "slides" / filename
    if not path.exists():
        return JSONResponse(status_code=404, content={"error": "Folie nicht gefunden"})
    return FileResponse(str(path))


# Statische Dateien (Frontend)
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5678, reload=False)
