# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RizzoClaw is a Telegram bot that forwards user text and voice messages to an AI agent built with the Agno framework. Voice messages are transcribed via OpenAI Whisper before being passed to the agent. Workshop project for the Rizzo AI Academy.

## Commands

```bash
# Install dependencies
uv sync

# Run the bot
uv run rizzoclaw

# Add a new dependency
uv add <package>
```

Entry point: `rizzoclaw = "rizzoclaw.bot:main"` (defined in pyproject.toml).

## Architecture

```
Telegram → bot.py (handlers) → agent.py (Agno agent) → response back to Telegram
                ↓ (voice)
         OpenAI Whisper transcription
```

- **`rizzoclaw/bot.py`** — Telegram bot with polling. Three handlers: `/start` command, text messages, voice/audio messages. Voice files are downloaded to temp files, transcribed with Whisper, then forwarded to the agent.
- **`rizzoclaw/agent.py`** — Agno `Agent` with GPT model, async SQLite memory (`agent.db`), agentic memory for user preferences, and tools (web search, file ops, Python, shell, HackerNews).
- **`rizzoclaw/config.py`** — Loads `TELEGRAM_BOT_TOKEN` and `OPENAI_API_KEY` from `.env`.

## Key Details

- Python 3.12, managed with **uv**
- All bot handlers and agent calls are **async**
- Bot responses and prompts are in **Italian**
- Agent uses `debug_mode=True` for verbose logging
- No test suite currently — testing is manual via Telegram
