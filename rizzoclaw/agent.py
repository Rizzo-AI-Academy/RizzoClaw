from agno.agent import Agent
from agno.db.sqlite import AsyncSqliteDb
from agno.memory.manager import MemoryManager
from agno.models.openai import OpenAIResponses, OpenAIChat
from agno.tools.hackernews import HackerNewsTools  # esempio di skill/tool
from agno.tools.websearch import WebSearchTools
from agno.tools.file import FileTools
from agno.tools.python import PythonTools
from agno.tools.shell import ShellTools

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

# 3. Agente con tools (skills), storage SQLite e memoria dinamica
agent = Agent(
    model=OpenAIChat(id=model_name),
    tools=[WebSearchTools(), FileTools(), PythonTools(), ShellTools(), HackerNewsTools()],
    db=db,
    memory_manager=memory_manager,
    enable_agentic_memory=True,         # memoria dinamica sulle preferenze
    add_history_to_context=True,
    num_history_runs=5,
    add_datetime_to_context=True,
    markdown=True,
    user_id="simone",
    session_id="simone",
    debug_mode=True,
    instructions=""
)


async def run_agent(user_message: str, user_id: str = "default_user") -> str:
    """Process a user message through the AI agent and return the response."""
    response = await agent.arun(user_message, user_id=user_id)
    return response.content