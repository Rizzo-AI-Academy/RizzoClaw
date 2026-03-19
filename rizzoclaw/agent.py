import httpx
import os
from datetime import datetime
from typing import Optional

from agno.agent import Agent
from agno.db.sqlite import AsyncSqliteDb
from agno.media import File as AgnoFile
from agno.memory.manager import MemoryManager
from agno.models.openai import OpenAIResponses, OpenAIChat
from agno.tools.hackernews import HackerNewsTools  # esempio di skill/tool
from agno.tools.websearch import WebSearchTools
from agno.tools.file import FileTools
from agno.tools.python import PythonTools
from agno.tools.shell import ShellTools
from agno.skills import LocalSkills, Skills

from rizzoclaw.config import TELEGRAM_BOT_TOKEN
from rizzoclaw.sem_mem import add_memory, search_memory

# Chat ID corrente — impostato prima di ogni chiamata all'agente
_current_chat_id: Optional[int] = None

# 1. Database SQLite asincrono
db = AsyncSqliteDb(db_file="./agent.db")
model_name = "gpt-5.2"

# 2. Memory Manager per catturare preferenze utente
memory_manager = MemoryManager(
    model=OpenAIChat(id=model_name),
    db=db,
    memory_capture_instructions="""\
        Raccogli il nome dell'utente,
        Raccogli le preferenze e gli interessi dell'utente,
        Raccogli informazioni su ciò che piace e non piace all'utente.
    """
)


async def send_file_to_telegram(file_path: str, caption: str = "") -> str:
    """Invia un file all'utente su Telegram.

    Args:
        file_path (str): Il percorso del file da inviare.
        caption (str): Didascalia opzionale per il file.
    """
    if _current_chat_id is None:
        return "Errore: nessuna chat Telegram attiva."

    if not os.path.isfile(file_path):
        return f"Errore: il file '{file_path}' non esiste."

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    async with httpx.AsyncClient() as client:
        with open(file_path, "rb") as f:
            resp = await client.post(
                url,
                data={"chat_id": _current_chat_id, "caption": caption},
                files={"document": (os.path.basename(file_path), f)},
            )
    if resp.status_code == 200:
        return f"File '{os.path.basename(file_path)}' inviato con successo."
    return f"Errore nell'invio del file: {resp.text}"


def cerca_memoria_semantica(query: str, n_results: int = 5) -> list[dict]:
    """Cerca nella memoria semantica conversazioni passate simili alla query.

    Args:
        query (str): Testo della ricerca semantica.
        n_results (int): Numero di risultati da restituire (default 5).

    Returns:
        Lista di dizionari con id, document, metadata e distance.
    """
    return search_memory(query=query, n_results=n_results)


# 3. Agente con tools (skills), storage SQLite e memoria dinamica
agent = Agent(
    model=OpenAIChat(id=model_name),
    tools=[WebSearchTools(), FileTools(), PythonTools(), ShellTools(), send_file_to_telegram, cerca_memoria_semantica],
    db=db,
    skills=Skills(loaders=[LocalSkills(str("/Users/simonerizzo/Git-projects/RizzoClaw/.agents/skills"))]),
    memory_manager=memory_manager,
    enable_agentic_memory=True,         # memoria dinamica sulle preferenze
    add_history_to_context=True,
    num_history_runs=50,
    add_datetime_to_context=True,
    markdown=True,
    user_id="simone_semantic2",
    session_id="simone_semantic2",
    debug_mode=False,
    instructions="Sei un Agente AI intelligente che vive nel mio pc. Il tuo nome è RizzoClaw. Hai accesso ai file system, puoi scrivere codice python, puoi lanciare comandi sulla shell, fare ricerche sul web, salvare le preferenze dell'utente in memoria ed anche cercare semanticamente nel database con tutte le conversazioni passate."
)


async def run_agent(
    user_message: str,
    user_id: str = "default_user",
    files: Optional[list[AgnoFile]] = None,
    chat_id: Optional[int] = None,
) -> str:
    """Process a user message through the AI agent and return the response."""
    global _current_chat_id
    _current_chat_id = chat_id

    response = await agent.arun(user_message, user_id=user_id, files=files)
    agent_reply = response.content

    today = datetime.now().strftime("%d-%m-%Y")
    metadata = {
        "date": today,
        "question": user_message,
        "answer": agent_reply,
    }

    # Indicizza la domanda con risposta nei metadati
    add_memory(user_message, metadata)
    # Indicizza la risposta con domanda nei metadati
    add_memory(agent_reply, metadata)

    return agent_reply
