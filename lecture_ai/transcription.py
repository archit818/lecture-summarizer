"""
Faster-Whisper transcription pipeline.
Runs in its own thread, polls audio chunks, transcribes, writes to DB.
"""

import threading
import logging
import time

logger = logging.getLogger(__name__)


class Transcriber:
    """
    Loads Faster-Whisper model (GPU first, CPU fallback).
    Polls audio chunks and writes transcript segments to the database.
    """

    def __init__(self, audio_capture, session_id: int):
        from . import config

        self._audio = audio_capture
        self._session_id = session_id
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._model = None
        self._model_size = config.WHISPER_MODEL

    def _load_model(self):
        """Load Faster-Whisper model with CUDA → CPU fallback."""
        from faster_whisper import WhisperModel
        from . import config

        # Try CUDA first
        try:
            logger.info(f"Loading Whisper model '{self._model_size}' on CUDA...")
            self._model = WhisperModel(
                self._model_size,
                device="cuda",
                compute_type=config.WHISPER_COMPUTE_TYPE,
            )
            logger.info("Whisper model loaded on CUDA.")
            return
        except Exception as e:
            logger.warning(f"CUDA not available: {e}. Falling back to CPU.")

        # Fallback to CPU
        try:
            self._model = WhisperModel(
                self._model_size,
                device="cpu",
                compute_type="int8",
            )
            logger.info("Whisper model loaded on CPU.")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}", exc_info=True)
            raise

    def _transcribe_loop(self):
        """Main transcription loop running in a thread."""
        from . import database

        self._load_model()

        while not self._stop_event.is_set():
            audio_chunk = self._audio.get_audio_chunk(timeout=2.0)
            if audio_chunk is None:
                continue

            try:
                segments, info = self._model.transcribe(
                    audio_chunk,
                    beam_size=5,
                    language=None,  # auto-detect
                    vad_filter=True,
                    vad_parameters=dict(
                        min_silence_duration_ms=500,
                        speech_pad_ms=200,
                    ),
                )

                for segment in segments:
                    text = segment.text.strip()
                    if text:
                        database.add_transcript(self._session_id, text)
                        database.touch_session(self._session_id)
                        logger.info(f"[{segment.start:.1f}s-{segment.end:.1f}s] {text}")

            except Exception as e:
                logger.error(f"Transcription error: {e}", exc_info=True)
                time.sleep(1)

    def start(self):
        """Start transcription in a background thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("Transcriber already running.")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._transcribe_loop, daemon=True, name="transcriber"
        )
        self._thread.start()
        logger.info("Transcriber started.")

    def stop(self):
        """Stop transcription and wait for the thread to finish."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=30)  # model may take time to finish
            self._thread = None
        logger.info("Transcriber stopped.")

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()
