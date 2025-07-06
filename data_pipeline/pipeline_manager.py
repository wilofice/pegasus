#!/usr/bin/env python3
"""
Data Pipeline Manager

Utility script to manage the data pipeline, monitor processing status,
and interact with the backend audio processing system.
"""
import asyncio
import sys
import argparse
from pathlib import Path
from typing import List, Optional
import json

# Local imports
from config import get_config, get_backend_settings
from backend_integration import BackendAudioProcessor

config = get_config()


class PipelineManager:
    """
    Manager for data pipeline operations and monitoring.
    """
    
    def __init__(self):
        self.processor = BackendAudioProcessor()
        self.config = config
    
    async def status(self):
        """Show pipeline status and configuration."""
        print("=== Data Pipeline Status ===")
        print(f"Source folder: {self.config.source_folder}")
        print(f"Processed folder: {self.config.processed_folder}")
        print(f"Log folder: {self.config.log_folder}")
        print()
        
        print("=== Backend Configuration ===")
        backend = get_backend_settings()
        print(f"Database URL: {backend.database_url[:50]}...")
        print(f"Transcription Engine: {backend.transcription_engine}")
        print(f"Whisper Model: {backend.whisper_model}")
        print(f"LLM Provider: {backend.llm_provider}")
        print(f"Audio Storage: {backend.audio_storage_path}")
        print()
        
        print("=== Folder Contents ===")
        await self._show_folder_contents()
    
    async def _show_folder_contents(self):
        """Show contents of pipeline folders."""
        # Source folder
        source_files = list(self.config.source_folder.glob("*"))
        print(f"Source folder ({len(source_files)} files):")
        for file_path in source_files[:10]:  # Show first 10
            size_mb = file_path.stat().st_size / (1024 * 1024) if file_path.is_file() else 0
            print(f"  - {file_path.name} ({size_mb:.1f} MB)")
        if len(source_files) > 10:
            print(f"  ... and {len(source_files) - 10} more files")
        print()
        
        # Log folder
        log_files = list(self.config.log_folder.glob("*.log"))
        print(f"Log files ({len(log_files)}):")
        for log_file in log_files:
            size_kb = log_file.stat().st_size / 1024
            print(f"  - {log_file.name} ({size_kb:.1f} KB)")
        print()
    
    async def process_file(self, file_path: str, user_id: str = None, language: str = None):
        """
        Manually process a specific file.
        
        Args:
            file_path: Path to the file to process
            user_id: User ID (defaults to config default)
            language: Language code (defaults to config default)
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            print(f"Error: File not found: {file_path}")
            return
        
        if not self.config.validate_file(file_path):
            print(f"Error: File validation failed: {file_path}")
            print(f"Supported formats: {self.config.supported_audio_formats}")
            return
        
        user_id = user_id or self.config.default_user_id
        language = language or self.config.default_language
        
        print(f"Processing file: {file_path}")
        print(f"User ID: {user_id}")
        print(f"Language: {language}")
        print()
        
        audio_id = await self.processor.process_audio_file_from_pipeline(
            file_path, user_id, language
        )
        
        if audio_id:
            print(f"✅ Successfully started processing: {audio_id}")
            print(f"You can check status with: python pipeline_manager.py check-status {audio_id}")
        else:
            print("❌ Failed to process file")
    
    async def check_status(self, audio_id: str):
        """
        Check processing status of an audio file.
        
        Args:
            audio_id: Audio file UUID
        """
        print(f"Checking status for audio ID: {audio_id}")
        
        status = await self.processor.get_processing_status(audio_id)
        
        if status:
            print(json.dumps(status, indent=2))
        else:
            print("❌ Audio file not found or status unavailable")
    
    async def list_recent(self, limit: int = 10):
        """
        List recent audio files processed by the pipeline.
        
        Args:
            limit: Number of files to show
        """
        try:
            from uuid import UUID
            from core.database import async_session
            from repositories.audio_repository import AudioRepository
            from sqlalchemy import select, desc
            from models.audio_file import AudioFile
            
            async with async_session() as db:
                audio_repo = AudioRepository(db)
                
                # Query recent files from data pipeline
                result = await db.execute(
                    select(AudioFile)
                    .where(AudioFile.user_id == self.config.default_user_id)
                    .order_by(desc(AudioFile.upload_timestamp))
                    .limit(limit)
                )
                
                audio_files = result.scalars().all()
                
                if audio_files:
                    print(f"=== Recent Pipeline Files (last {len(audio_files)}) ===")
                    for audio_file in audio_files:
                        status_icon = self._get_status_icon(audio_file.processing_status)
                        print(f"{status_icon} {audio_file.original_filename}")
                        print(f"   ID: {audio_file.id}")
                        print(f"   Status: {audio_file.processing_status}")
                        print(f"   Uploaded: {audio_file.upload_timestamp}")
                        if audio_file.original_transcript:
                            transcript_preview = audio_file.original_transcript[:100] + "..." if len(audio_file.original_transcript) > 100 else audio_file.original_transcript
                            print(f"   Transcript: {transcript_preview}")
                        print()
                else:
                    print("No files found from data pipeline")
                    
        except Exception as e:
            print(f"Error listing files: {e}")
    
    def _get_status_icon(self, status):
        """Get icon for processing status."""
        icons = {
            "uploaded": "📤",
            "transcribing": "🎯",
            "improving": "✨",
            "completed": "✅",
            "failed": "❌"
        }
        return icons.get(status, "❓")
    
    async def clean_logs(self, days: int = 7):
        """
        Clean old log files.
        
        Args:
            days: Remove log files older than this many days
        """
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        removed_count = 0
        
        for log_file in self.config.log_folder.glob("*.log"):
            file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
            if file_time < cutoff_date:
                log_file.unlink()
                removed_count += 1
                print(f"Removed: {log_file.name}")
        
        print(f"Cleaned {removed_count} log files older than {days} days")


async def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description="Data Pipeline Manager")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Status command
    subparsers.add_parser("status", help="Show pipeline status")
    
    # Process command
    process_parser = subparsers.add_parser("process", help="Process a specific file")
    process_parser.add_argument("file_path", help="Path to the file to process")
    process_parser.add_argument("--user-id", help="User ID for the file")
    process_parser.add_argument("--language", help="Language code (e.g., en, fr)")
    
    # Check status command
    check_parser = subparsers.add_parser("check-status", help="Check processing status")
    check_parser.add_argument("audio_id", help="Audio file UUID")
    
    # List recent command
    list_parser = subparsers.add_parser("list-recent", help="List recent processed files")
    list_parser.add_argument("--limit", type=int, default=10, help="Number of files to show")
    
    # Clean logs command
    clean_parser = subparsers.add_parser("clean-logs", help="Clean old log files")
    clean_parser.add_argument("--days", type=int, default=7, help="Remove files older than N days")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = PipelineManager()
    
    try:
        if args.command == "status":
            await manager.status()
        elif args.command == "process":
            await manager.process_file(args.file_path, args.user_id, args.language)
        elif args.command == "check-status":
            await manager.check_status(args.audio_id)
        elif args.command == "list-recent":
            await manager.list_recent(args.limit)
        elif args.command == "clean-logs":
            await manager.clean_logs(args.days)
    except KeyboardInterrupt:
        print("\nOperation cancelled")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())