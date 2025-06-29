#!/usr/bin/env python3
"""Test the tags endpoint directly to get the exact 422 error details."""
import requests
import json
import sys

def test_tags_endpoint(base_url="http://localhost:9000"):
    """Test the /api/audio/tags endpoint and show the exact error."""
    url = f"{base_url}/api/audio/tags"
    
    print(f"🧪 Testing tags endpoint: {url}")
    print("-" * 50)
    
    try:
        # Make the request
        response = requests.get(url, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print(f"Content-Type: {response.headers.get('content-type', 'unknown')}")
        
        # Try to parse response body
        try:
            if response.headers.get('content-type', '').startswith('application/json'):
                error_detail = response.json()
                print(f"Response Body (JSON):")
                print(json.dumps(error_detail, indent=2))
            else:
                print(f"Response Body (Text):")
                print(response.text)
        except json.JSONDecodeError:
            print(f"Response Body (Raw):")
            print(response.text)
        
        # Analysis
        if response.status_code == 422:
            print("\n🔍 422 Error Analysis:")
            print("This typically means:")
            print("1. Database connection failed")
            print("2. Database schema is missing/incorrect") 
            print("3. Dependencies (get_db) failed to resolve")
            print("4. Pydantic model validation failed")
            
            # Try to extract specific error
            try:
                error_data = response.json()
                if 'detail' in error_data:
                    print(f"\n❌ Specific Error: {error_data['detail']}")
                    
                    # Check for common issues
                    detail_str = str(error_data['detail']).lower()
                    if 'database' in detail_str or 'connection' in detail_str:
                        print("💡 LIKELY CAUSE: Database connection issue")
                    elif 'column' in detail_str or 'relation' in detail_str:
                        print("💡 LIKELY CAUSE: Missing database columns/tables")
                    elif 'dependency' in detail_str:
                        print("💡 LIKELY CAUSE: FastAPI dependency injection failed")
                    
            except:
                pass
                
        return response.status_code == 200
        
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - make sure the server is running")
        return False
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False

def test_health_endpoint(base_url="http://localhost:9000"):
    """Test if the server is running by hitting the health endpoint."""
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ Server is running at {base_url}")
            return True
        else:
            print(f"⚠️  Server responded with {response.status_code}")
            return False
    except Exception:
        print(f"❌ Server is not responding at {base_url}")
        return False

def test_database_connection():
    """Test database connection directly."""
    try:
        import asyncio
        import sys
        from pathlib import Path
        
        # Add parent directory to path
        sys.path.append(str(Path(__file__).parent))
        
        async def check_db():
            try:
                from core.database import async_session
                
                print("🔍 Testing database connection...")
                async with async_session() as session:
                    from sqlalchemy import text
                    result = await session.execute(text("SELECT 1"))
                    value = result.scalar()
                    if value == 1:
                        print("✅ Database connection successful")
                        return True
                    else:
                        print("❌ Database connection failed")
                        return False
            except Exception as e:
                print(f"❌ Database connection failed: {e}")
                return False
        
        return asyncio.run(check_db())
        
    except Exception as e:
        print(f"❌ Database test setup failed: {e}")
        return False

def main():
    """Main test function."""
    print("🚨 Debugging 422 Error for /api/audio/tags")
    print("=" * 60)
    
    # Test if server is running
    server_ok = test_health_endpoint()
    
    if not server_ok:
        print("\n💡 Start the server first: python3 main.py")
        return False
    
    # Test database connection
    print()
    db_ok = test_database_connection()
    
    # Test the problematic endpoint
    print()
    endpoint_ok = test_tags_endpoint()
    
    print("\n" + "=" * 60)
    print("🎯 Test Summary:")
    print(f"   Server running: {'✅' if server_ok else '❌'}")
    print(f"   Database connection: {'✅' if db_ok else '❌'}")
    print(f"   Tags endpoint: {'✅' if endpoint_ok else '❌'}")
    
    if not db_ok:
        print("\n💡 SOLUTION: Fix database connection")
        print("   - Check .env file for DATABASE_URL")
        print("   - Ensure PostgreSQL is running")
        print("   - Run migration: python3 resolve_migration_error.py")
    elif not endpoint_ok:
        print("\n💡 SOLUTION: Check the detailed error message above")
        print("   The response body should show the exact issue")
    
    return endpoint_ok

if __name__ == "__main__":
    # Allow custom base URL
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://192.168.1.15:9000"
    success = main()
    sys.exit(0 if success else 1)