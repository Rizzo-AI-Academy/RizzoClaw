import os
import chromadb
from chromadb.config import Settings
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

CHROMA_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "chroma_db")

_client: chromadb.ClientAPI | None = None
_collection: chromadb.Collection | None = None
_openai: OpenAI | None = None

COLLECTION_NAME = "semantic_memory"
EMBEDDING_MODEL = "text-embedding-3-small"


def _get_chroma_collection() -> chromadb.Collection:
    global _client, _collection
    if _collection is None:
        os.makedirs(CHROMA_DB_PATH, exist_ok=True)
        _client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def _get_openai() -> OpenAI:
    global _openai
    if _openai is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY non trovata nel .env")
        _openai = OpenAI(api_key=api_key)
    return _openai


def _embed(text: str) -> list[float]:
    response = _get_openai().embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


def add_memory(text: str, metadata: dict, doc_id: str | None = None) -> str:
    """
    Aggiunge un testo alla memoria semantica con i metadati forniti.

    Args:
        text: il testo da memorizzare
        metadata: dizionario con i metadati associati al testo
        doc_id: ID univoco del documento (generato automaticamente se None)

    Returns:
        l'ID del documento inserito
    """
    from datetime import datetime
    import uuid

    collection = _get_chroma_collection()

    if doc_id is None:
        doc_id = str(uuid.uuid4())

    metadata.setdefault("datetime", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    embedding = _embed(text)

    collection.upsert(
        ids=[doc_id],
        embeddings=[embedding],
        documents=[text],
        metadatas=[metadata],
    )

    return doc_id


def search_memory(query: str, n_results: int = 5, where: dict | None = None) -> list[dict]:
    """
    Cerca nella memoria semantica i documenti più simili alla query.

    Args:
        query: testo della query di ricerca
        n_results: numero massimo di risultati da restituire
        where: filtro opzionale sui metadati (es. {"category": "news"})

    Returns:
        lista di dizionari con chiavi: id, document, metadata, distance
    """
    collection = _get_chroma_collection()

    query_embedding = _embed(query)

    kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where

    results = collection.query(**kwargs)

    output = []
    ids = results["ids"][0]
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    for doc_id, doc, meta, dist in zip(ids, documents, metadatas, distances):
        output.append({
            "id": doc_id,
            "document": doc,
            "metadata": meta,
            "datetime": meta.get("datetime"),
            "distance": dist,
        })

    return output


def delete_memory(doc_id: str) -> None:
    """Rimuove un documento dalla memoria semantica per ID."""
    collection = _get_chroma_collection()
    collection.delete(ids=[doc_id])


def count_memories() -> int:
    """Restituisce il numero totale di documenti nella memoria semantica."""
    return _get_chroma_collection().count()


# out = search_memory("simone", n_results=2)
# print(out)
