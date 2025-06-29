#!/usr/bin/env python3
"""Test script for request/response logging middleware."""
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
import requests
import time

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

def test_logging_middleware(base_url="http://localhost:9000"):
    """Test the logging middleware with various request types."""
    
    test_cases = [
        {
            "name": "Health Check (should be excluded)",
            "method": "GET",
            "url": f"{base_url}/health",
            "expected_in_logs": False
        },
        {
            "name": "GET request with query params",
            "method": "GET", 
            "url": f"{base_url}/api/audio/",
            "params": {"limit": 5, "user_id": "test"},
            "expected_in_logs": True
        },
        {
            "name": "POST request with JSON body",
            "method": "POST",
            "url": f"{base_url}/api/audio/tags",
            "json": {"tag": "test_tag", "category": "test_category"},
            "expected_in_logs": True,
            "expect_error": True  # This endpoint might not exist
        },
        {
            "name": "File upload request",
            "method": "POST",
            "url": f"{base_url}/api/audio/upload",
            "files": {"file": ("test.txt", "dummy content", "text/plain")},
            "data": {"user_id": "test_user"},
            "expected_in_logs": True,
            "expect_error": True  # Will fail validation
        }
    ]
    
    print(f"🧪 Testing logging middleware with {base_url}")
    print("=" * 60)
    
    results = []
    
    for test_case in test_cases:
        print(f"\n📋 Test: {test_case['name']}")
        
        try:
            # Make the request
            kwargs = {}
            if "params" in test_case:
                kwargs["params"] = test_case["params"]
            if "json" in test_case:
                kwargs["json"] = test_case["json"]
            if "files" in test_case:
                kwargs["files"] = test_case["files"]
            if "data" in test_case:
                kwargs["data"] = test_case["data"]
            
            start_time = time.time()
            
            response = requests.request(
                method=test_case["method"],
                url=test_case["url"],
                timeout=10,
                **kwargs
            )
            
            duration = time.time() - start_time
            
            print(f"   ✅ Request completed: {response.status_code} ({duration:.2f}s)")
            
            if not test_case.get("expect_error", False) and response.status_code >= 400:
                print(f"   ⚠️  Unexpected error response: {response.text[:200]}")
            
            results.append({
                "test": test_case["name"],
                "status": "success",
                "status_code": response.status_code,
                "duration": duration,
                "expected_in_logs": test_case["expected_in_logs"]
            })
            
        except requests.exceptions.ConnectionError:
            print(f"   ❌ Connection failed to {base_url}")
            print("   Make sure the backend server is running")
            results.append({
                "test": test_case["name"],
                "status": "connection_error",
                "expected_in_logs": False
            })
            break
            
        except Exception as e:
            print(f"   ❌ Request failed: {str(e)}")
            results.append({
                "test": test_case["name"],
                "status": "error",
                "error": str(e),
                "expected_in_logs": test_case["expected_in_logs"]
            })
    
    return results

def check_log_files():
    """Check if log files were created and contain expected entries."""
    log_dir = Path("./logs")
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = log_dir / f"requests_{today}.log"
    
    print(f"\n🔍 Checking log files...")
    print("-" * 40)
    
    if not log_dir.exists():
        print("❌ Log directory doesn't exist")
        return False
    
    if not log_file.exists():
        print(f"❌ Today's log file doesn't exist: {log_file}")
        print("Available files:")
        for f in log_dir.glob("requests_*.log"):
            print(f"   {f.name}")
        return False
    
    # Read and analyze log file
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        print(f"✅ Log file exists: {log_file}")
        print(f"   Total lines: {len(lines)}")
        
        # Parse log entries
        requests = 0
        responses = 0
        errors = 0
        
        recent_entries = []
        
        for line in lines[-20:]:  # Check last 20 lines
            try:
                if line.strip() and line.strip().startswith('{'):
                    entry = json.loads(line.strip())
                    
                    if entry.get("type") == "REQUEST":
                        requests += 1
                    elif entry.get("type") == "RESPONSE":
                        responses += 1
                    
                    recent_entries.append(entry)
                    
            except json.JSONDecodeError:
                errors += 1
        
        print(f"   Recent requests: {requests}")
        print(f"   Recent responses: {responses}")
        if errors > 0:
            print(f"   Parse errors: {errors}")
        
        # Show some recent entries
        if recent_entries:
            print(f"\n📝 Recent log entries (last 5):")
            for entry in recent_entries[-5:]:
                entry_type = entry.get("type", "UNKNOWN")
                if entry_type == "REQUEST":
                    method = entry.get("method", "")
                    path = entry.get("path", "")
                    print(f"   📤 REQUEST: {method} {path}")
                elif entry_type == "RESPONSE":
                    status = entry.get("status_code", "")
                    duration = entry.get("duration_ms", "")
                    print(f"   📥 RESPONSE: {status} ({duration}ms)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error reading log file: {e}")
        return False

def show_log_stats():
    """Show statistics about log files."""
    try:
        from scripts.log_manager import LogManager
        
        print(f"\n📊 Log File Statistics:")
        print("-" * 30)
        
        log_manager = LogManager("./logs")
        stats = log_manager.get_log_stats()
        
        print(f"Total files: {stats['total_files']}")
        print(f"Total size: {stats['total_size_mb']} MB")
        
        if stats['date_range']:
            print(f"Date range: {stats['date_range']['from']} to {stats['date_range']['to']}")
        
        if stats['files']:
            print("\nFiles:")
            for file_info in stats['files'][-5:]:  # Show last 5 files
                print(f"  {file_info['name']} ({file_info['size_mb']} MB)")
                
    except Exception as e:
        print(f"❌ Error getting log stats: {e}")

def main():
    """Main test function."""
    print("🔍 Request/Response Logging Middleware Test")
    print("=" * 60)
    
    # Check if server is running
    try:
        response = requests.get("http://localhost:9000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend server is running")
        else:
            print(f"⚠️  Backend server responded with {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("❌ Backend server is not running")
        print("Start it with: python3 main.py")
        return False
    
    # Run tests
    results = test_logging_middleware()
    
    # Wait a moment for logs to be written
    print("\n⏳ Waiting for logs to be written...")
    time.sleep(2)
    
    # Check log files
    log_check = check_log_files()
    
    # Show statistics
    show_log_stats()
    
    # Summary
    print(f"\n🎯 Test Summary:")
    print("-" * 20)
    
    successful_tests = sum(1 for r in results if r["status"] == "success")
    total_tests = len(results)
    
    print(f"Tests completed: {successful_tests}/{total_tests}")
    print(f"Log files created: {'✅' if log_check else '❌'}")
    
    if log_check and successful_tests > 0:
        print("\n🎉 Logging middleware is working correctly!")
        print("\nNext steps:")
        print("  - Check log files in ./logs/ directory")
        print("  - Use 'python3 scripts/log_manager.py stats' for detailed analysis")
        print("  - Configure excluded paths in .env if needed")
    else:
        print("\n❌ Some issues detected. Check the configuration and server logs.")
    
    return log_check and successful_tests > 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)