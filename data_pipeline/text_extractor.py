from pathlib import Path
import re
import logging

try:
    import eml_parser
except Exception:  # pragma: no cover - dependency may be missing
    eml_parser = None

LOGGER = logging.getLogger(__name__)


def extract_text(file_path: Path) -> str:
    file_path = Path(file_path)
    LOGGER.info("Extracting text from %s", file_path)
    if file_path.suffix in {".txt", ".md"}:
        return file_path.read_text(encoding="utf-8")
    if file_path.suffix == ".eml":
        if eml_parser is None:
            raise RuntimeError("eml_parser package not installed")
        with file_path.open("rb") as f:
            eml = eml_parser.EmlParser().decode_email_bytes(f.read())
            body = eml.get("body", {})
            text = body.get("content", "")
            return text
    if file_path.suffix == ".txt" and "whatsapp" in file_path.name.lower():
        text = file_path.read_text(encoding="utf-8")
        return re.sub(r"^\[[^\]]+\]\s[^:]+:\s", "", text, flags=re.MULTILINE)
    raise ValueError(f"Unsupported file type: {file_path.suffix}")
