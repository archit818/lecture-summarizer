"""
QR code scanner.
Takes screenshots, detects QR codes, deduplicates, stores, and sends via Telegram.
"""

import threading
import logging
import time
import re
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# Regex for URLs
_URL_PATTERN = re.compile(r"https?://[^\s]+", re.IGNORECASE)


class QRScanner:
    """
    Scans for QR codes on screen at a fixed interval.

    Dedup logic:
    - First time a URL is seen in a session → screenshot + DB + Telegram.
    - Same URL within 10 min → ignore entirely.
    - Same URL after 10+ min gap → add timestamp entry in DB only (no screenshot, no Telegram).
    - Same URL in a different session → treat as new (screenshot + DB + Telegram).
    """

    def __init__(self, session_id: int):
        from . import config

        self._session_id = session_id
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

        # Pending confirmations: url → count of consecutive scans
        self._pending: dict[str, int] = {}

        # In-memory dedup cache for the current session:
        # url → datetime of last stored occurrence
        self._seen_urls: dict[str, datetime] = {}

        self._scan_interval = config.QR_SCAN_INTERVAL
        self._confirm_count = config.QR_CONFIRM_COUNT
        self._reappear_gap = timedelta(minutes=config.QR_REAPPEAR_GAP_MINUTES)
        self._screenshots_dir = config.SCREENSHOTS_DIR

    @staticmethod
    def _capture_screen():
        """Take a screenshot of the primary monitor."""
        from PIL import ImageGrab

        return ImageGrab.grab()

    def _decode_qr(self, image) -> list[str]:
        """Decode QR codes from a PIL image, return URL strings only."""
        import cv2
        import numpy as np

        # Convert PIL to OpenCV
        frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        urls = []
        # Use OpenCV's built-in QR detector
        detector = cv2.QRCodeDetector()
        
        # detectAndDecode can find one QR. For multiple, detectAndDecodeMulti is needed (OpenCV 4.5.2+)
        try:
            retval, info, points, straight_qrcode = detector.detectAndDecodeMulti(frame)
            if retval and info:
                for data in info:
                    if data and _URL_PATTERN.match(data):
                        urls.append(data)
        except AttributeError:
            # Fallback for older OpenCV versions
            data, points, straight_qrcode = detector.detectAndDecode(frame)
            if data and _URL_PATTERN.match(data):
                urls.append(data)
        
        return urls

    def _save_screenshot(self, image, url: str) -> str:
        """Save a screenshot to disk. Returns the file path."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Sanitize URL for filename
        safe_name = re.sub(r"[^\w]", "_", url)[:60]
        filename = f"qr_{timestamp}_{safe_name}.png"
        filepath = self._screenshots_dir / filename
        image.save(str(filepath))
        logger.info(f"Screenshot saved: {filepath}")
        return str(filepath)

    def _handle_confirmed_url(self, url: str, image):
        """Handle a URL that has been confirmed by consecutive scans."""
        from . import database, telegram_bot

        now = datetime.now()

        if url in self._seen_urls:
            last_seen = self._seen_urls[url]
            gap = now - last_seen

            if gap < self._reappear_gap:
                # Within 10 min gap — silently ignore
                return

            # After 10+ min gap — add timestamp entry only (no screenshot, no Telegram)
            database.add_qr_code(self._session_id, url, image_path=None)
            database.touch_session(self._session_id)
            self._seen_urls[url] = now
            logger.info(f"QR re-seen after {gap}: {url} (timestamp only)")
            return

        # First time in this session — full flow
        screenshot_path = self._save_screenshot(image, url)
        database.add_qr_code(self._session_id, url, image_path=screenshot_path)
        database.touch_session(self._session_id)
        self._seen_urls[url] = now

        # Send via Telegram
        try:
            telegram_bot.send_photo(screenshot_path, caption=f"🔗 QR Detected:\n{url}")
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")

        logger.info(f"QR detected and sent: {url}")

    def _scan_loop(self):
        """Main scanning loop running in a thread."""
        while not self._stop_event.is_set():
            try:
                image = QRScanner._capture_screen()
                detected_urls = self._decode_qr(image)

                # Update pending confirmations
                current_set = set(detected_urls)

                # Increment or add pending
                new_pending = {}
                for url in current_set:
                    count = self._pending.get(url, 0) + 1
                    new_pending[url] = count

                    if count >= self._confirm_count:
                        self._handle_confirmed_url(url, image)

                # URLs not in this scan lose their pending count
                self._pending = new_pending

            except Exception as e:
                logger.error(f"QR scan error: {e}", exc_info=True)

            # Wait for next scan interval
            self._stop_event.wait(self._scan_interval)

    def start(self):
        """Start QR scanning in a background thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("QR scanner already running.")
            return

        self._stop_event.clear()
        self._pending.clear()
        self._seen_urls.clear()
        self._thread = threading.Thread(
            target=self._scan_loop, daemon=True, name="qr-scanner"
        )
        self._thread.start()
        logger.info("QR scanner started.")

    def stop(self):
        """Stop QR scanning."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=10)
            self._thread = None
        logger.info("QR scanner stopped.")

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()
