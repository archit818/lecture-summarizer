"""
Configuration for the Lecture AI system.
Loads secrets from .env, defines all paths and constants.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

# --- Paths ---
BASE_DIR = _PROJECT_ROOT
DATA_DIR = BASE_DIR / "data"
SCREENSHOTS_DIR = DATA_DIR / "screenshots"
OUTPUT_DIR = DATA_DIR / "output"
DB_PATH = DATA_DIR / "lecture_ai.db"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
SCREENSHOTS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# --- Telegram ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# --- Auth ---
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "changeme")

# --- Whisper ---
WHISPER_MODEL = "small"  # "tiny", "base", "small", "medium", "large-v2"
WHISPER_DEVICE = "auto"  # "auto" will try cuda then cpu
WHISPER_COMPUTE_TYPE = "float16"  # "float16" for GPU, "int8" for CPU

# --- Audio ---
AUDIO_SAMPLE_RATE = 16000  # Whisper expects 16kHz mono
AUDIO_CHANNELS = 1
AUDIO_CHUNK_DURATION = 5  # seconds per chunk sent to Whisper

# --- QR Scanner ---
QR_SCAN_INTERVAL = 3  # seconds between screen captures
QR_CONFIRM_COUNT = 2  # consecutive scans needed to confirm a QR
QR_REAPPEAR_GAP_MINUTES = 10  # minutes before a re-seen URL gets a timestamp entry

# --- Ollama ---
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3"

# --- Session ---
STALE_SESSION_MINUTES = 5  # auto-close after this many minutes of inactivity

# --- Server ---
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5000
