# 🎓 Lecture AI Intelligence System

A powerful, local AI system designed to capture, transcribe, and summarize lectures in real-time. This system monitors your system audio and screen to provide an automated study assistant that sends key information directly to your Telegram.

## 🌟 Key Features
- **Real-time Transcription**: Uses **Faster-Whisper** to convert system audio into text immediately.
- **QR Code Detection**: Automatically scans your screen for QR codes, captures them, and sends the links to Telegram.
- **Local AI Summarization**: Uses **Ollama (Llama 3)** to generate smart summaries of your lectures without sending data to the cloud.
- **Telegram Integration**: Get instant alerts for QR codes and a final `.docx` report with the full transcript and summary.
- **Local Privacy**: Everything runs on your machine—no expensive API keys or cloud privacy concerns.

---

## 🛠️ Prerequisites

Before starting, ensure you have the following installed:

1. **Python 3.10+**
2. **FFmpeg**: Required for audio processing.
   - [Download here](https://ffmpeg.org/download.html) and add the `bin` folder to your Windows PATH.
3. **Ollama**: Required for summarization.
   - [Download here](https://ollama.com/) and run `ollama pull llama3`.
4. **C++ Redistributable**: Usually pre-installed on Windows, required for OpenCV/PyZbar.

---

## 🚀 Getting Started

### 1. Setup Environment
Clone the project and create a virtual environment:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configure Credentials
Create a `.env` file in the root directory (use the provided template):
```env
# Get from @BotFather on Telegram
TELEGRAM_BOT_TOKEN=your_bot_token

# Get from @userinfobot on Telegram
TELEGRAM_CHAT_ID=your_chat_id

# Create any secret string for local security
AUTH_TOKEN=your_secret_token
```

### 3. Start the System
You need **two terminal windows** open:

**Terminal 1 (The Engine):**
Start the main server which handles the recording and processing.
```powershell
python -m lecture_ai.main
```

**Terminal 2 (The Controls):**
Use the control script to manage your lecture sessions.
```powershell
python control.py start    # Begin recording
python control.py status   # Check if system is active
python control.py stop     # End lecture & receive summary on Telegram
```

---

## 📁 Project Structure
- `/lecture_ai`: Core logic (Audio capture, Transcription, QR scanning).
- `/data`: Local database, screenshots, and generated summaries.
- `control.py`: Simple CLI tool to manage sessions.
- `.env`: Your private configuration.

---

## 🔧 Troubleshooting
- **No Transcription?** Ensure your "Stereo Mix" is enabled in Windows Sound Settings.
- **Telegram Error 400?** Make sure you have clicked **"START"** on your bot in the Telegram app first.
- **Ollama Error?** Ensure the Ollama app is running in your system tray.
