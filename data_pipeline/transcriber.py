from pathlib import Path
import tempfile
import logging

try:
    import whisper
except Exception:  # pragma: no cover - dependency may be missing
    whisper = None

LOGGER = logging.getLogger(__name__)


def transcribe(file_path: Path) -> str:
    """Transcribe an audio file to text using OpenAI Whisper."""
    if whisper is None:
        raise RuntimeError("whisper package not installed")
    model = whisper.load_model("base")
    LOGGER.info("Transcribing %s", file_path)
    with tempfile.TemporaryDirectory() as tmpdir:
        result = model.transcribe(str(file_path), fp16=False)
        text = result.get("text", "")
    return text.strip()
