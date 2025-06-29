"""Engine that reacts to pipeline notifications."""
from services import vector_db_client, llm_client


def process_notification(payload: dict) -> None:
    """Analyze new data and potentially notify users."""
    file_path = payload.get("file_path")
    if not file_path:
        return
    embedding = vector_db_client.embed(file_path)
    passages = vector_db_client.search(embedding, top_k=3)
    prompt = f"Summarize: {passages}. Should notify?"
    llm_client.generate(prompt)
