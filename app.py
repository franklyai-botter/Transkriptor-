"""
NeuralNautic Transcriptor — Desktop-Launcher.

Startet das FastAPI-Backend in einem Hintergrund-Thread und oeffnet
ein natives pywebview-Fenster (statt eines Browser-Tabs).

Schliessen des Fensters beendet automatisch den Backend-Server.
"""
import os
import sys
import time
import threading
import subprocess
import urllib.request
from pathlib import Path

import webview
import uvicorn

# Backend importieren (FastAPI-App-Objekt heisst dort `app`)
from backend import app as fastapi_app


HOST = "127.0.0.1"
PORT = 5678
URL  = f"http://{HOST}:{PORT}"

BASE_DIR = Path(__file__).parent
WORK_DIR = BASE_DIR / "transcriptor_jobs"

_server: uvicorn.Server | None = None


class Api:
    """Wird vom Frontend via window.pywebview.api aufgerufen."""

    def open_job_folder(self, job_id: str) -> bool:
        """Oeffnet den Job-Ordner im Windows-Explorer."""
        # Sicherheits-Filter: nur alphanumerische Job-IDs erlauben
        if not job_id or not all(c.isalnum() or c in "-_" for c in job_id):
            return False
        job_dir = WORK_DIR / job_id
        if not job_dir.exists() or not job_dir.is_dir():
            return False
        try:
            os.startfile(str(job_dir))  # Windows-spezifisch, oeffnet Explorer
            return True
        except Exception:
            try:
                subprocess.Popen(["explorer", str(job_dir)])
                return True
            except Exception:
                return False


def _run_server():
    """uvicorn im Hintergrund-Thread starten."""
    global _server
    config = uvicorn.Config(
        fastapi_app,
        host=HOST,
        port=PORT,
        log_level="warning",
        access_log=False,
    )
    _server = uvicorn.Server(config)
    _server.run()


def _wait_for_server(timeout: float = 15.0) -> bool:
    """Wartet bis /health antwortet."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{URL}/health", timeout=1) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.25)
    return False


def _on_window_closed():
    """Sauber beenden wenn das Fenster geschlossen wird."""
    if _server:
        _server.should_exit = True


def main():
    # 1) Backend-Thread starten
    t = threading.Thread(target=_run_server, daemon=True)
    t.start()

    # 2) Auf Health-Check warten
    if not _wait_for_server():
        print("[Transcriptor] Backend reagiert nicht. Abbruch.", file=sys.stderr)
        sys.exit(1)

    # 3) pywebview-Fenster oeffnen
    base = Path(__file__).parent
    icon_path = base / "nn-star.ico"

    window = webview.create_window(
        title="NeuralNautic Transcriptor",
        url=URL,
        js_api=Api(),
        width=1280,
        height=860,
        min_size=(960, 640),
        background_color="#0A2028",
        frameless=False,
    )
    window.events.closed += _on_window_closed

    # Icon nur setzen wenn vorhanden (pywebview API variiert je nach Backend)
    kwargs = {"debug": False}
    if icon_path.exists():
        kwargs["icon"] = str(icon_path)
    try:
        webview.start(**kwargs)
    except TypeError:
        # Aeltere pywebview-Version ohne icon-Parameter
        webview.start(debug=False)


if __name__ == "__main__":
    main()
