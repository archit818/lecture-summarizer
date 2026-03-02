"""
Telegram Bot integration.
Simple requests-based calls to Telegram Bot API for sending messages, photos, and documents.
"""

import logging
import requests

from . import config

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.telegram.org/bot{token}"


def _api_url(method: str) -> str:
    token = config.TELEGRAM_BOT_TOKEN
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not configured in .env")
    return f"{_BASE_URL.format(token=token)}/{method}"


def _chat_id() -> str:
    chat_id = config.TELEGRAM_CHAT_ID
    if not chat_id:
        raise ValueError("TELEGRAM_CHAT_ID not configured in .env")
    return chat_id


def send_message(text: str):
    """Send a text message to the configured Telegram chat."""
    try:
        resp = requests.post(
            _api_url("sendMessage"),
            json={"chat_id": _chat_id(), "text": text, "parse_mode": "HTML"},
            timeout=30,
        )
        resp.raise_for_status()
        logger.info("Telegram message sent.")
    except Exception as e:
        logger.error(f"Telegram send_message failed: {e}")


def send_photo(photo_path: str, caption: str = ""):
    """Send a photo to the configured Telegram chat."""
    try:
        with open(photo_path, "rb") as f:
            resp = requests.post(
                _api_url("sendPhoto"),
                data={"chat_id": _chat_id(), "caption": caption},
                files={"photo": f},
                timeout=60,
            )
        resp.raise_for_status()
        logger.info(f"Telegram photo sent: {photo_path}")
    except Exception as e:
        logger.error(f"Telegram send_photo failed: {e}")


def send_document(doc_path: str, caption: str = ""):
    """Send a document to the configured Telegram chat."""
    try:
        with open(doc_path, "rb") as f:
            resp = requests.post(
                _api_url("sendDocument"),
                data={"chat_id": _chat_id(), "caption": caption},
                files={"document": f},
                timeout=120,
            )
        resp.raise_for_status()
        logger.info(f"Telegram document sent: {doc_path}")
    except Exception as e:
        logger.error(f"Telegram send_document failed: {e}")
