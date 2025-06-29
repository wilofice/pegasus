#!/usr/bin/env python3
"""Log management utility for request/response logs."""
import json
import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import argparse


class LogManager:
    """Utility class for managing request/response log files."""
    
    def __init__(self, log_dir: str = "./logs"):
        self.log_dir = Path(log_dir)
        
    def list_log_files(self) -> List[Path]:
        """List all request log files."""
        if not self.log_dir.exists():
            return []
        
        return sorted(self.log_dir.glob("requests_*.log"))
    
    def get_log_stats(self) -> Dict[str, any]:
        """Get statistics about log files."""
        log_files = self.list_log_files()
        
        if not log_files:
            return {"total_files": 0, "total_size_mb": 0, "date_range": None}
        
        total_size = sum(f.stat().st_size for f in log_files)
        
        # Extract dates from filenames
        dates = []
        for f in log_files:
            try:
                date_str = f.stem.replace("requests_", "")
                dates.append(datetime.strptime(date_str, "%Y-%m-%d").date())
            except ValueError:
                continue
        
        date_range = None
        if dates:
            dates.sort()
            date_range = {"from": dates[0].isoformat(), "to": dates[-1].isoformat()}
        
        return {
            "total_files": len(log_files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "date_range": date_range,
            "files": [
                {
                    "name": f.name,
                    "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
                    "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                }
                for f in log_files
            ]
        }
    
    def compress_old_logs(self, days_old: int = 7) -> List[Path]:
        """Compress log files older than specified days."""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        compressed_files = []
        
        for log_file in self.list_log_files():
            try:
                # Extract date from filename
                date_str = log_file.stem.replace("requests_", "")
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                
                if file_date < cutoff_date:
                    compressed_file = log_file.with_suffix(".log.gz")
                    
                    # Skip if already compressed
                    if compressed_file.exists():
                        continue
                    
                    # Compress the file
                    with open(log_file, 'rb') as f_in:
                        with gzip.open(compressed_file, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    
                    # Remove original file
                    log_file.unlink()
                    compressed_files.append(compressed_file)
                    
            except (ValueError, OSError) as e:
                print(f"Error compressing {log_file}: {e}")
                continue
        
        return compressed_files
    
    def delete_old_logs(self, days_old: int = 30) -> List[Path]:
        """Delete log files older than specified days."""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        deleted_files = []
        
        # Check both .log and .log.gz files
        for pattern in ["requests_*.log", "requests_*.log.gz"]:
            for log_file in self.log_dir.glob(pattern):
                try:
                    # Extract date from filename
                    date_str = log_file.stem.replace("requests_", "").replace(".log", "")
                    file_date = datetime.strptime(date_str, "%Y-%m-%d")
                    
                    if file_date < cutoff_date:
                        log_file.unlink()
                        deleted_files.append(log_file)
                        
                except (ValueError, OSError) as e:
                    print(f"Error deleting {log_file}: {e}")
                    continue
        
        return deleted_files
    
    def analyze_log_file(self, date: str) -> Dict[str, any]:
        """Analyze a specific log file for the given date."""
        log_file = self.log_dir / f"requests_{date}.log"
        
        if not log_file.exists():
            # Try compressed version
            log_file = self.log_dir / f"requests_{date}.log.gz"
            if not log_file.exists():
                return {"error": f"Log file for {date} not found"}
        
        stats = {
            "date": date,
            "total_requests": 0,
            "total_responses": 0,
            "status_codes": {},
            "methods": {},
            "paths": {},
            "avg_duration_ms": 0,
            "errors": []
        }
        
        total_duration = 0
        response_count = 0
        
        try:
            # Open file (handle both regular and gzipped)
            if log_file.suffix == ".gz":
                file_handle = gzip.open(log_file, 'rt', encoding='utf-8')
            else:
                file_handle = open(log_file, 'r', encoding='utf-8')
            
            with file_handle as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        # Skip non-JSON lines
                        if not line.strip() or not line.strip().startswith('{'):
                            continue
                        
                        # Parse JSON log entry
                        log_entry = json.loads(line.strip())
                        
                        if log_entry.get("type") == "REQUEST":
                            stats["total_requests"] += 1
                            
                            # Count methods
                            method = log_entry.get("method", "UNKNOWN")
                            stats["methods"][method] = stats["methods"].get(method, 0) + 1
                            
                            # Count paths
                            path = log_entry.get("path", "UNKNOWN")
                            stats["paths"][path] = stats["paths"].get(path, 0) + 1
                        
                        elif log_entry.get("type") == "RESPONSE":
                            stats["total_responses"] += 1
                            response_count += 1
                            
                            # Count status codes
                            status = log_entry.get("status_code", 0)
                            stats["status_codes"][status] = stats["status_codes"].get(status, 0) + 1
                            
                            # Calculate average duration
                            duration = log_entry.get("duration_ms", 0)
                            total_duration += duration
                    
                    except json.JSONDecodeError as e:
                        stats["errors"].append(f"Line {line_num}: Invalid JSON - {str(e)}")
                    except Exception as e:
                        stats["errors"].append(f"Line {line_num}: {str(e)}")
        
        except Exception as e:
            return {"error": f"Failed to read log file: {str(e)}"}
        
        # Calculate average duration
        if response_count > 0:
            stats["avg_duration_ms"] = round(total_duration / response_count, 2)
        
        return stats
    
    def search_logs(self, date: str, search_term: str, log_type: str = "both") -> List[Dict]:
        """Search for specific terms in log files."""
        log_file = self.log_dir / f"requests_{date}.log"
        results = []
        
        if not log_file.exists():
            # Try compressed version
            log_file = self.log_dir / f"requests_{date}.log.gz"
            if not log_file.exists():
                return []
        
        try:
            # Open file (handle both regular and gzipped)
            if log_file.suffix == ".gz":
                file_handle = gzip.open(log_file, 'rt', encoding='utf-8')
            else:
                file_handle = open(log_file, 'r', encoding='utf-8')
            
            with file_handle as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        # Skip non-JSON lines
                        if not line.strip() or not line.strip().startswith('{'):
                            continue
                        
                        # Parse JSON log entry
                        log_entry = json.loads(line.strip())
                        
                        # Filter by log type
                        entry_type = log_entry.get("type", "").lower()
                        if log_type != "both" and entry_type != log_type.lower():
                            continue
                        
                        # Search in the entire log entry
                        if search_term.lower() in json.dumps(log_entry).lower():
                            results.append({
                                "line_number": line_num,
                                "log_entry": log_entry
                            })
                    
                    except json.JSONDecodeError:
                        continue
                    except Exception:
                        continue
        
        except Exception as e:
            print(f"Error searching log file: {e}")
        
        return results


def main():
    """Command-line interface for log management."""
    parser = argparse.ArgumentParser(description="Manage request/response log files")
    parser.add_argument("--log-dir", default="./logs", help="Log directory path")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # List command
    subparsers.add_parser("list", help="List all log files")
    
    # Stats command
    subparsers.add_parser("stats", help="Show log file statistics")
    
    # Compress command
    compress_parser = subparsers.add_parser("compress", help="Compress old log files")
    compress_parser.add_argument("--days", type=int, default=7, help="Compress files older than N days")
    
    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete old log files")
    delete_parser.add_argument("--days", type=int, default=30, help="Delete files older than N days")
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze log file for specific date")
    analyze_parser.add_argument("date", help="Date in YYYY-MM-DD format")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search logs for specific terms")
    search_parser.add_argument("date", help="Date in YYYY-MM-DD format")
    search_parser.add_argument("term", help="Search term")
    search_parser.add_argument("--type", choices=["request", "response", "both"], default="both", help="Log entry type")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    log_manager = LogManager(args.log_dir)
    
    if args.command == "list":
        files = log_manager.list_log_files()
        if files:
            print(f"Found {len(files)} log files:")
            for f in files:
                size_mb = f.stat().st_size / (1024 * 1024)
                print(f"  {f.name} ({size_mb:.2f} MB)")
        else:
            print("No log files found")
    
    elif args.command == "stats":
        stats = log_manager.get_log_stats()
        print("Log File Statistics:")
        print(f"  Total files: {stats['total_files']}")
        print(f"  Total size: {stats['total_size_mb']} MB")
        if stats['date_range']:
            print(f"  Date range: {stats['date_range']['from']} to {stats['date_range']['to']}")
    
    elif args.command == "compress":
        compressed = log_manager.compress_old_logs(args.days)
        if compressed:
            print(f"Compressed {len(compressed)} files:")
            for f in compressed:
                print(f"  {f.name}")
        else:
            print("No files to compress")
    
    elif args.command == "delete":
        deleted = log_manager.delete_old_logs(args.days)
        if deleted:
            print(f"Deleted {len(deleted)} files:")
            for f in deleted:
                print(f"  {f.name}")
        else:
            print("No files to delete")
    
    elif args.command == "analyze":
        analysis = log_manager.analyze_log_file(args.date)
        if "error" in analysis:
            print(f"Error: {analysis['error']}")
        else:
            print(f"Analysis for {args.date}:")
            print(f"  Requests: {analysis['total_requests']}")
            print(f"  Responses: {analysis['total_responses']}")
            print(f"  Average duration: {analysis['avg_duration_ms']} ms")
            print(f"  Status codes: {analysis['status_codes']}")
            print(f"  Methods: {analysis['methods']}")
            if analysis['errors']:
                print(f"  Errors: {len(analysis['errors'])}")
    
    elif args.command == "search":
        results = log_manager.search_logs(args.date, args.term, args.type)
        if results:
            print(f"Found {len(results)} matches:")
            for result in results[:10]:  # Show first 10 results
                print(f"  Line {result['line_number']}: {result['log_entry'].get('type')} - {result['log_entry'].get('method', '')} {result['log_entry'].get('path', '')}")
            if len(results) > 10:
                print(f"  ... and {len(results) - 10} more")
        else:
            print("No matches found")


if __name__ == "__main__":
    main()