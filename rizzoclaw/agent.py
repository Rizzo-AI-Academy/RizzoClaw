import httpx
import os
import uuid
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
        Cattura e aggiorna continuamente le seguenti informazioni sull'utente:

        IDENTITÀ
        - Nome, soprannome o come preferisce essere chiamato
        - Professione, ruolo lavorativo e settore
        - Lingua preferita e stile comunicativo (formale/informale)

        PREFERENZE TECNICHE
        - Linguaggi di programmazione e framework preferiti
        - Strumenti, editor e ambienti di sviluppo usati
        - Stack tecnologico dei progetti su cui lavora
        - Approcci e pattern architetturali preferiti

        PROGETTI E OBIETTIVI
        - Progetti attuali e relativi obiettivi
        - Problemi ricorrenti o sfide che affronta
        - Risultati e traguardi raggiunti

        VITA PERSONALE E FAMIGLIA
        - Stato civile e nome del partner/coniuge
        - Figli (nomi, età, caratteristiche rilevanti)
        - Familiari stretti menzionati (genitori, fratelli, ecc.)
        - Fede religiosa o spirituale e pratiche associate
        - Valori etici e morali importanti per l'utente
        - Luogo in cui vive (città, paese, contesto)
        - Ricorrenze e date importanti (compleanni, anniversari)

        INTERESSI E PERSONALITÀ
        - Argomenti che appassionano l'utente (tech e non)
        - Hobby e attività nel tempo libero
        - Cose che non gli piacciono o che trova frustranti
        - Valori e priorità personali

        COMPORTAMENTO CON L'AGENTE
        - Come preferisce ricevere le risposte (brevi/dettagliate, con esempi, con codice)
        - Feedback espliciti dati all'agente (cosa ha apprezzato o criticato)
        - Abitudini di lavoro (orari, ritmi, frequenza di utilizzo)

        Aggiorna le informazioni esistenti se emergono dettagli nuovi o contraddittori.
        Non duplicare informazioni già presenti in memoria.
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
    skills=Skills(loaders=[LocalSkills(str(os.path.join(os.path.dirname(__file__), "..", ".agents", "skills")))]),
    memory_manager=memory_manager,
    enable_agentic_memory=True,         # memoria dinamica sulle preferenze
    add_history_to_context=True,
    num_history_runs=50,
    add_datetime_to_context=True,
    markdown=True,
    user_id="simone_semantic3",
    session_id="simone_semantic3",
    debug_mode=True,
    instructions="Sei un Agente AI intelligente che vive nel mio pc. Leggi la skilss agent-memory e parti dal file BRAIN.md e PROGRESS.md.  Il tuo nome è RizzoClaw. Hai accesso ai file system, puoi scrivere codice python, puoi lanciare comandi sulla shell, fare ricerche sul web, salvare le preferenze dell'utente in memoria ed anche cercare semanticamente nel database con tutte le conversazioni passate."
)


SESSION_TOKEN_LIMIT = 200_000


async def _maybe_flush_session() -> bool:
    """Se i token della sessione superano il limite, ordina all'agente di salvare
    tutto in memoria tramite la skill agent-memory, poi resetta la sessione.

    Returns:
        True se il flush è stato eseguito, False altrimenti.
    """
    try:
        session_metrics = agent.get_session_metrics()
        total_tokens = session_metrics.total_tokens or 0
    except Exception:
        return False

    if total_tokens < SESSION_TOKEN_LIMIT:
        return False

    flush_prompt = (
        "Hai raggiunto il limite di token per questa sessione. "
        "Segui le istruzioni della skill agent-memory: "
        "1) aggiorna BRAIN.md con il riassunto di tutto ciò che è stato discusso finora, "
        "le decisioni prese, il contesto utente e gli eventuali task in sospeso; "
        "2) salva il dettaglio completo della sessione in memories/yyyy-mm-gg/session.md; "
        "3) se sono presenti task di coding attivi, aggiorna PROGRESS.md. "
        "Dopo aver salvato conferma con: 'Memoria salvata. La sessione verrà resettata.'"
    )
    await agent.arun(flush_prompt)

    new_session_id = f"simone_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    agent.session_id = new_session_id
    return True


async def run_agent(
    user_message: str,
    user_id: str = "default_user",
    files: Optional[list[AgnoFile]] = None,
    chat_id: Optional[int] = None,
) -> str:
    """Process a user message through the AI agent and return the response."""
    global _current_chat_id
    _current_chat_id = chat_id

    flushed = await _maybe_flush_session()

    response = await agent.arun(user_message, user_id=user_id, files=files)
    agent_reply = response.content

    try:
        session_metrics = agent.get_session_metrics()
        total_tokens = session_metrics.total_tokens or 0
        print(f"[TOKEN USAGE] Sessione: {total_tokens:,} / {SESSION_TOKEN_LIMIT:,} token")
        if flushed:
            print(f"[MEMORY FLUSH] Triggered a {total_tokens:,} token — sessione resettata: {agent.session_id}")
    except Exception:
        pass

    if flushed:
        agent_reply = "_(Sessione resettata automaticamente: limite token raggiunto)_\n\n" + agent_reply

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
