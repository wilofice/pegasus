"""Reactive orchestrator combining context and user messages."""
from ..services import vector_db_client, llm_client


def handle_chat(message: str) -> str:
    """Return the LLM-generated reply using vector context."""
    embedding = vector_db_client.embed(message)
    passages = vector_db_client.search(embedding, top_k=3)
    prompt = f"Context: {passages}\nUser: {message}\nAnswer:"
    return llm_client.generate(prompt)
