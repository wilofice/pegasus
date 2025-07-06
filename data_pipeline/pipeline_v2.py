"""
Enhanced pipeline that reuses backend logic for audio processing.

This version of the pipeline integrates with the existing backend
audio processing workflow, avoiding code duplication while maintaining
the file-watching capability.
"""
import logging
import signal
import sys
from pathlib import Path

from watcher import watch
from backend_integration import create_pipeline_callback

# Configure logging
log_dir = Path(__file__).parent / 'logs'
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'pipeline_v2.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
LOGGER = logging.getLogger("pipeline_v2")


class EnhancedPipeline:
    """
    Enhanced pipeline that uses backend processing logic.
    """
    
    def __init__(self, source_folder: Path):
        self.source_folder = Path(source_folder)
        self.source_folder.mkdir(exist_ok=True)
        self.observer = None
        self.callback = create_pipeline_callback()
        self.running = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def start(self):
        """Start the pipeline with file watching."""
        try:
            LOGGER.info(f"Starting enhanced pipeline watching: {self.source_folder}")
            
            # Start file watcher
            self.observer = watch(self.source_folder, self.callback)
            self.running = True
            
            LOGGER.info("Pipeline started successfully")
            LOGGER.info("Supported audio formats: .mp3, .m4a, .wav, .ogg, .webm, .aac, .flac")
            LOGGER.info("Place audio files in the source_data folder to trigger processing")
            
            # Keep the process alive
            while self.running:
                try:
                    # Use observer.join() with timeout for responsiveness
                    if self.observer:
                        self.observer.join(timeout=1.0)
                except KeyboardInterrupt:
                    break
                    
        except Exception as e:
            LOGGER.error(f"Error starting pipeline: {e}", exc_info=True)
            self.stop()
    
    def stop(self):
        """Stop the pipeline gracefully."""
        LOGGER.info("Stopping pipeline...")
        self.running = False
        
        if self.observer:
            self.observer.stop()
            self.observer.join()
            
        LOGGER.info("Pipeline stopped")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        LOGGER.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)
    
    def process_existing_files(self):
        """Process any existing files in the source folder."""
        LOGGER.info("Checking for existing files in source folder...")
        
        audio_extensions = {'.mp3', '.m4a', '.wav', '.ogg', '.webm', '.aac', '.flac'}
        existing_files = []
        
        for ext in audio_extensions:
            existing_files.extend(self.source_folder.glob(f"*{ext}"))
            existing_files.extend(self.source_folder.glob(f"*{ext.upper()}"))
        
        if existing_files:
            LOGGER.info(f"Found {len(existing_files)} existing audio files")
            for file_path in existing_files:
                LOGGER.info(f"Processing existing file: {file_path}")
                self.callback(file_path)
        else:
            LOGGER.info("No existing audio files found")
    
    async def monitor_job_progress(self, audio_id: str, check_interval: int = 30):
        """
        Monitor job progress for an audio file.
        
        Args:
            audio_id: Audio file UUID
            check_interval: Seconds between progress checks
        """
        import asyncio
        from backend_integration import BackendAudioProcessor
        
        processor = BackendAudioProcessor()
        
        while True:
            try:
                progress = await processor.get_job_progress(audio_id)
                if not progress:
                    LOGGER.warning(f"No progress info found for audio {audio_id}")
                    break
                
                LOGGER.info(f"Progress for {audio_id}: {progress['completed_jobs']}/{progress['total_jobs']} jobs completed")
                
                # Check if all jobs are completed or failed
                if progress['completed_jobs'] + progress['failed_jobs'] >= progress['total_jobs']:
                    LOGGER.info(f"All jobs completed for audio {audio_id}")
                    break
                
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                LOGGER.error(f"Error monitoring progress for {audio_id}: {e}")
                break


def main():
    """Main entry point for the enhanced pipeline."""
    # Default source folder
    source_folder = Path(__file__).parent / 'source_data'
    
    # Allow custom source folder via command line
    if len(sys.argv) > 1:
        source_folder = Path(sys.argv[1])
    
    # Create and start pipeline
    pipeline = EnhancedPipeline(source_folder)
    
    try:
        # Process any existing files first
        pipeline.process_existing_files()
        
        # Start watching for new files
        pipeline.start()
        
    except KeyboardInterrupt:
        LOGGER.info("Received keyboard interrupt")
        pipeline.stop()
    except Exception as e:
        LOGGER.error(f"Pipeline error: {e}", exc_info=True)
        pipeline.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()