from lecture_ai import telegram_bot, config
import sys

print(f"Testing Telegram Bot with:")
print(f"Token: {config.TELEGRAM_BOT_TOKEN[:10]}...{config.TELEGRAM_BOT_TOKEN[-5:]}")
print(f"Chat ID: {config.TELEGRAM_CHAT_ID}")

try:
    telegram_bot.send_message("🚀 Lecture AI: Telegram connection test successful!")
    print("\n✅ Test message sent! Check your Telegram app.")
    print("If you didn't receive it, your CHAT_ID might be wrong.")
except Exception as e:
    print(f"\n❌ Failed: {e}")
