import logging
from pathlib import Path

from watcher import watch
from transcriber import transcribe
from text_extractor import extract_text
from segmenter import chunk_text
from vectorizer import embed
from storage import insert
from notifier import send_webhook

logging.basicConfig(
    filename=Path(__file__).with_name('logs/pipeline.log'),
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)
LOGGER = logging.getLogger("pipeline")


def process_file(path: Path):
    try:
        if path.suffix in {'.mp3', '.m4a'}:
            text = transcribe(path)
        else:
            text = extract_text(path)
        chunks = chunk_text(text)
        vectors = embed(chunks)
        metadatas = [{"file": path.name, "chunk": i} for i, _ in enumerate(chunks)]
        insert(vectors, metadatas)
        send_webhook({"file": path.name, "chunks": len(chunks)})
    except Exception as exc:
        LOGGER.error("Error processing %s: %s", path, exc)


def main():
    source_folder = Path(__file__).with_name('source_data')
    watch(source_folder, process_file)
    LOGGER.info("Pipeline started")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        LOGGER.info("Pipeline stopped")


if __name__ == "__main__":
    main()
