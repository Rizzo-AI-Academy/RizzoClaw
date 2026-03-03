"""Telegram bot that forwards messages to the AI agent."""

import logging
import tempfile

from openai import AsyncOpenAI
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from rizzoclaw.agent import run_agent
from rizzoclaw.config import OPENAI_API_KEY, TELEGRAM_BOT_TOKEN

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command."""
    await update.message.reply_text("Ciao! Sono RizzoClaw, chiedimi pure quello che vuoi!")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Forward every text message to the AI agent and reply with the result."""
    user_text = update.message.text
    logger.info("Message from %s: %s", update.effective_user.username, user_text)

    response = await run_agent(user_text)
    await update.message.reply_text(response)


async def transcribe_audio(file_path: str) -> str:
    """Transcribe an audio file using OpenAI Whisper."""
    with open(file_path, "rb") as audio_file:
        transcription = await openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
        )
    return transcription.text


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Download a voice/audio message, transcribe it, and forward to the agent."""
    voice = update.message.voice or update.message.audio
    file = await context.bot.get_file(voice.file_id)

    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        await file.download_to_drive(tmp.name)
        tmp_path = tmp.name

    logger.info("Voice message from %s, transcribing…", update.effective_user.username)
    transcript = await transcribe_audio(tmp_path)
    logger.info("Transcript: %s", transcript)

    await update.message.reply_text(f"🎤 Trascrizione: {transcript}")

    response = await run_agent(transcript)
    await update.message.reply_text(response)


def create_app() -> Application:
    """Build and return the Telegram Application (bot)."""
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    return app


def main() -> None:
    """Entry point — start polling for updates."""
    app = create_app()
    logger.info("Bot started, polling…")
    app.run_polling()
