#!/usr/bin/env python3
"""Test script for the audio upload endpoint."""
import requests
import io
import sys
from pathlib import Path

def test_upload_endpoint(base_url="http://localhost:9000"):
    """Test the audio upload endpoint with a dummy file."""
    
    # Create a dummy audio file content
    dummy_audio_content = b"dummy audio file content for testing"
    
    # Test different scenarios
    test_cases = [
        {
            "filename": "test.m4a",
            "content_type": "audio/mp4",
            "description": "Valid M4A file with correct MIME type"
        },
        {
            "filename": "test.mp3", 
            "content_type": "audio/mpeg",
            "description": "Valid MP3 file with correct MIME type"
        },
        {
            "filename": "test.m4a",
            "content_type": "application/octet-stream",
            "description": "Valid M4A file with generic MIME type (should work with fallback)"
        },
        {
            "filename": "test.txt",
            "content_type": "text/plain",
            "description": "Invalid file type (should fail)"
        }
    ]
    
    print(f"Testing audio upload endpoint at {base_url}/api/audio/upload\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}: {test_case['description']}")
        print(f"  File: {test_case['filename']}")
        print(f"  MIME Type: {test_case['content_type']}")
        
        try:
            # Prepare the file upload
            files = {
                'file': (
                    test_case['filename'],
                    io.BytesIO(dummy_audio_content),
                    test_case['content_type']
                )
            }
            
            data = {
                'user_id': 'test_user'
            }
            
            # Make the request
            response = requests.post(
                f"{base_url}/api/audio/upload",
                files=files,
                data=data,
                timeout=10
            )
            
            print(f"  Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"  ✅ SUCCESS: Audio ID = {result.get('id', 'N/A')}")
                print(f"  Processing Status: {result.get('processing_status', 'N/A')}")
            else:
                print(f"  ❌ FAILED: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print(f"  ❌ CONNECTION ERROR: Could not connect to {base_url}")
            print("  Make sure the backend server is running on the correct port")
        except Exception as e:
            print(f"  ❌ ERROR: {str(e)}")
        
        print()

def test_health_endpoint(base_url="http://localhost:9000"):
    """Test the health endpoint to verify server is running."""
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ Server is running at {base_url}")
            return True
        else:
            print(f"❌ Server responded with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to server at {base_url}")
        return False
    except Exception as e:
        print(f"❌ Error checking server health: {str(e)}")
        return False

if __name__ == "__main__":
    # Check if custom base URL is provided
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:9000"
    
    print("🧪 Audio Upload Endpoint Test\n")
    
    # First check if server is running
    if test_health_endpoint(base_url):
        print()
        test_upload_endpoint(base_url)
    else:
        print("\nPlease start the backend server first:")
        print("  cd backend")
        print("  python main.py")
        sys.exit(1)