"""
WASAPI loopback audio capture for Windows.
Captures system audio (what you hear) and provides chunks for transcription.
"""

import threading
import queue
import logging
import time
import numpy as np

logger = logging.getLogger(__name__)


class AudioCapture:
    """
    Captures system audio via WASAPI loopback on Windows.
    Audio is resampled to 16kHz mono float32 for Whisper.
    """

    def __init__(self, sample_rate: int = 16000, chunk_duration: int = 5):
        self.target_sr = sample_rate
        self.chunk_duration = chunk_duration
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._audio_queue: queue.Queue = queue.Queue(maxsize=50)
        self._device_info = None

    def _find_loopback_device(self) -> dict | None:
        """Find the loopback device (Stereo Mix or WASAPI Loopback)."""
        import sounddevice as sd

        try:
            devices = sd.query_devices()
            
            # 1. Prioritize Stereo Mix (very reliable on Windows if enabled)
            for i, dev in enumerate(devices):
                name = dev["name"].lower()
                if "stereo mix" in name and dev["max_input_channels"] > 0:
                    logger.info(f"Found Stereo Mix device: [{i}] {dev['name']}")
                    return {"index": i, **dev}

            # 2. Look for explicit 'loopback' in WASAPI devices
            for i, dev in enumerate(devices):
                name = dev["name"].lower()
                hostapi_info = sd.query_hostapis(dev["hostapi"])
                if hostapi_info["name"] == "Windows WASAPI":
                    if "loopback" in name:
                        logger.info(f"Found WASAPI loopback device: [{i}] {dev['name']}")
                        return {"index": i, **dev}

            # 3. Fallback: use default output if WASAPI allows it (though rare without loopback flag)
            default_out = sd.default.device[1]
            if default_out is not None and default_out >= 0:
                dev = sd.query_devices(default_out)
                logger.info(f"Using default output as last resort: {dev['name']}")
                return {"index": default_out, **dev}

        except Exception as e:
            logger.error(f"Error finding loopback device: {e}")
        return None

    def _capture_loop(self):
        """Main capture loop running in a thread."""
        import sounddevice as sd

        device = self._find_loopback_device()
        if device is None:
            logger.error("No loopback device found. Audio capture cannot start.")
            return

        device_sr = int(device.get("default_samplerate", 16000))
        # Match the device's input channels
        channels = device.get("max_input_channels", 2)
        if channels == 0:
            channels = 1
            
        logger.info(
            f"Audio capture: device={device['name']}, sr={device_sr}, ch={channels}"
        )

        buffer = []
        samples_needed = int(device_sr * self.chunk_duration)

        def callback(indata, frames, time_info, status):
            if status:
                logger.warning(f"Audio status: {status}")
            buffer.append(indata.copy())

        try:
            # We removed WasapiSettings(loopback=True) as it caused errors
            # Some versions use a specific device, some use a flag. 
            # If the device is correctly selected (like Stereo Mix), no extra settings needed.
            with sd.InputStream(
                device=device["index"],
                samplerate=device_sr,
                channels=channels,
                dtype="float32",
                callback=callback,
                blocksize=1024,
            ):
                while not self._stop_event.is_set():
                    time.sleep(0.5)

                    # Check if we have enough audio
                    total_samples = sum(b.shape[0] for b in buffer)
                    if total_samples >= samples_needed:
                        # Concatenate and process
                        audio = np.concatenate(buffer, axis=0)
                        buffer.clear()

                        # Convert to mono if stereo
                        if audio.ndim > 1 and audio.shape[1] > 1:
                            audio = np.mean(audio, axis=1)
                        elif audio.ndim > 1:
                            audio = audio[:, 0]

                        # Resample to target sample rate if needed
                        if device_sr != self.target_sr:
                            ratio = self.target_sr / device_sr
                            new_len = int(len(audio) * ratio)
                            indices = np.linspace(0, len(audio) - 1, new_len)
                            audio = np.interp(indices, np.arange(len(audio)), audio)

                        audio = audio.astype(np.float32)

                        try:
                            self._audio_queue.put_nowait(audio)
                        except queue.Full:
                            # Drop oldest chunk
                            try:
                                self._audio_queue.get_nowait()
                            except queue.Empty:
                                pass
                            self._audio_queue.put_nowait(audio)

        except Exception as e:
            logger.error(f"Audio capture error: {e}", exc_info=True)

    def start(self):
        """Start audio capture in a background thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("Audio capture already running.")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._capture_loop, daemon=True, name="audio-capture")
        self._thread.start()
        logger.info("Audio capture started.")

    def stop(self):
        """Stop audio capture and wait for the thread to finish."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=10)
            self._thread = None
        # Clear remaining audio
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break
        logger.info("Audio capture stopped.")

    def get_audio_chunk(self, timeout: float = 1.0) -> np.ndarray | None:
        """Get the next audio chunk. Returns None if no audio available."""
        try:
            return self._audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()
