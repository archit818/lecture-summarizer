"""
Session manager.
Orchestrates audio capture, transcription, and QR scanning threads.
Handles session lifecycle and stale session cleanup.
"""

import threading
import logging
import time

from . import config, database
from .audio import AudioCapture
from .transcription import Transcriber
from .qr_scanner import QRScanner
from . import telegram_bot, summarizer

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages the lifecycle of a capture session."""

    def __init__(self):
        self._session_id: int | None = None
        self._audio: AudioCapture | None = None
        self._transcriber: Transcriber | None = None
        self._qr_scanner: QRScanner | None = None
        self._watchdog_thread: threading.Thread | None = None
        self._watchdog_stop = threading.Event()
        self._lock = threading.Lock()

    @property
    def is_active(self) -> bool:
        return self._session_id is not None

    @property
    def session_id(self) -> int | None:
        return self._session_id

    def start_session(self) -> dict:
        """Start a new capture session."""
        with self._lock:
            if self.is_active:
                return {"error": "Session already active", "session_id": self._session_id}

            # Create DB session
            session_id = database.create_session()
            self._session_id = session_id

            # Start audio capture
            self._audio = AudioCapture(
                sample_rate=config.AUDIO_SAMPLE_RATE,
                chunk_duration=config.AUDIO_CHUNK_DURATION,
            )
            self._audio.start()

            # Start transcriber
            self._transcriber = Transcriber(self._audio, session_id)
            self._transcriber.start()

            # Start QR scanner
            self._qr_scanner = QRScanner(session_id)
            self._qr_scanner.start()

            # Start watchdog
            self._start_watchdog()

            logger.info(f"Session {session_id} started.")
            return {"status": "started", "session_id": session_id}

    def stop_session(self) -> dict:
        """Stop the current session and generate summary."""
        with self._lock:
            if not self.is_active:
                return {"error": "No active session"}

            session_id = self._session_id

            # Stop watchdog first
            self._stop_watchdog()

            # Stop threads in reverse order
            if self._qr_scanner:
                self._qr_scanner.stop()
                self._qr_scanner = None

            if self._transcriber:
                self._transcriber.stop()
                self._transcriber = None

            if self._audio:
                self._audio.stop()
                self._audio = None

            # End session in DB
            database.end_session(session_id)
            self._session_id = None

        # Generate summary and send document (outside lock)
        try:
            doc_path = summarizer.generate_document(session_id)
            telegram_bot.send_document(doc_path, caption=f"📄 Session {session_id} Summary")
            logger.info(f"Session {session_id} completed. Document sent.")
        except Exception as e:
            logger.error(f"Post-session processing failed: {e}", exc_info=True)

        return {"status": "stopped", "session_id": session_id}

    def get_status(self) -> dict:
        """Return current session status."""
        if not self.is_active:
            return {"status": "idle", "session_id": None}

        return {
            "status": "active",
            "session_id": self._session_id,
            "audio_running": self._audio.is_running() if self._audio else False,
            "transcriber_running": self._transcriber.is_running() if self._transcriber else False,
            "qr_scanner_running": self._qr_scanner.is_running() if self._qr_scanner else False,
        }

    # ---- Stale session watchdog ----

    def _start_watchdog(self):
        self._watchdog_stop.clear()
        self._watchdog_thread = threading.Thread(
            target=self._watchdog_loop, daemon=True, name="session-watchdog"
        )
        self._watchdog_thread.start()

    def _stop_watchdog(self):
        self._watchdog_stop.set()
        if self._watchdog_thread:
            self._watchdog_thread.join(timeout=5)
            self._watchdog_thread = None

    def _watchdog_loop(self):
        """Check for stale sessions every 60 seconds."""
        while not self._watchdog_stop.is_set():
            self._watchdog_stop.wait(60)
            if self._watchdog_stop.is_set():
                break

            try:
                stale = database.get_stale_sessions(config.STALE_SESSION_MINUTES)
                for s in stale:
                    if s["id"] == self._session_id:
                        logger.warning(
                            f"Session {s['id']} is stale. Auto-closing."
                        )
                        # Release lock before calling stop_session
                        threading.Thread(
                            target=self.stop_session, daemon=True
                        ).start()
                        return
            except Exception as e:
                logger.error(f"Watchdog error: {e}", exc_info=True)
