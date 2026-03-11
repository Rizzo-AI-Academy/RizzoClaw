"""Telegram bot that forwards messages to the AI agent."""

import logging
import os
import tempfile

from agno.media import File as AgnoFile
from openai import AsyncOpenAI
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from rizzoclaw.agent import run_agent
from rizzoclaw.config import ALLOWED_USER_ID, OPENAI_API_KEY, TELEGRAM_BOT_TOKEN

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def is_user_allowed(update: Update) -> bool:
    """Check if the user is allowed to use the bot."""
    user = update.effective_user
    logger.info(
        "Richiesta da utente: id=%s, username=%s, nome=%s %s",
        user.id, user.username, user.first_name, user.last_name or "",
    )
    if ALLOWED_USER_ID and user.id != ALLOWED_USER_ID:
        logger.warning("Utente non autorizzato: id=%s", user.id)
        return False
    return True


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command."""
    if not is_user_allowed(update):
        await update.message.reply_text("Non sei autorizzato ad usare questo bot.")
        return
    await update.message.reply_text("Ciao! Sono RizzoClaw, chiedimi pure quello che vuoi!")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Forward every text message to the AI agent and reply with the result."""
    if not is_user_allowed(update):
        await update.message.reply_text("Non sei autorizzato ad usare questo bot.")
        return

    user_text = update.message.text
    chat_id = update.effective_chat.id
    response = await run_agent(user_text, chat_id=chat_id)
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
    if not is_user_allowed(update):
        await update.message.reply_text("Non sei autorizzato ad usare questo bot.")
        return

    voice = update.message.voice or update.message.audio
    file = await context.bot.get_file(voice.file_id)

    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        await file.download_to_drive(tmp.name)
        tmp_path = tmp.name

    logger.info("Messaggio vocale, trascrizione in corso…")
    transcript = await transcribe_audio(tmp_path)
    logger.info("Transcript: %s", transcript)

    await update.message.reply_text(f"🎤 Trascrizione: {transcript}")

    chat_id = update.effective_chat.id
    response = await run_agent(transcript, chat_id=chat_id)
    await update.message.reply_text(response)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Download a document/file, pass it to the agent as an AgnoFile."""
    if not is_user_allowed(update):
        await update.message.reply_text("Non sei autorizzato ad usare questo bot.")
        return

    document = update.message.document
    file = await context.bot.get_file(document.file_id)
    file_name = document.file_name or "file"
    suffix = os.path.splitext(file_name)[1] or ""

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        await file.download_to_drive(tmp.name)
        tmp_path = tmp.name

    logger.info("File ricevuto: %s (%s)", file_name, document.mime_type)

    with open(tmp_path, "rb") as f:
        agno_file = AgnoFile(content=f.read(), name=file_name, mime_type=document.mime_type)

    user_text = update.message.caption or f"Ho inviato il file: {file_name}"
    user_text += f"\n\nIl file è salvato in: {tmp_path}"
    chat_id = update.effective_chat.id
    response = await run_agent(user_text, files=[agno_file], chat_id=chat_id)
    await update.message.reply_text(response)


def create_app() -> Application:
    """Build and return the Telegram Application (bot)."""
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    return app


def main() -> None:
    """Entry point — start polling for updates."""
    app = create_app()
    logger.info("Bot started, polling…")
    app.run_polling()
