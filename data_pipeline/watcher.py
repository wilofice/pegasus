from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
import logging

LOGGER = logging.getLogger(__name__)

class NewFileHandler(FileSystemEventHandler):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def on_created(self, event):
        if not event.is_directory:
            LOGGER.info("New file detected: %s", event.src_path)
            self.callback(Path(event.src_path))


def watch(folder: Path, callback):
    """Start watching a folder and call *callback* for each new file."""
    folder = Path(folder)
    observer = Observer()
    handler = NewFileHandler(callback)
    observer.schedule(handler, str(folder), recursive=False)
    observer.start()
    LOGGER.info("Watching %s", folder)
    return observer
