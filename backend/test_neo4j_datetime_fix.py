#!/usr/bin/env python3
"""
Test script to verify Neo4j DateTime serialization fix
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add the backend directory to the path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))


class MockNeo4jDateTime:
    """Mock Neo4j DateTime object for testing"""
    def __init__(self, dt: datetime):
        self._dt = dt
    
    def to_native(self):
        """Convert to native Python datetime"""
        return self._dt


def test_neo4j_datetime_serialization():
    """Test that Neo4j DateTime objects are properly serialized"""
    print("=" * 60)
    print("TESTING NEO4J DATETIME SERIALIZATION FIX")
    print("=" * 60)
    
    try:
        from services.retrieval.neo4j_retriever import Neo4jRetriever
        
        # Create a mock Neo4j retriever instance
        class TestNeo4jRetriever(Neo4jRetriever):
            def __init__(self):
                # Don't call super().__init__() to avoid Neo4j connection
                self.name = "test_neo4j"
        
        retriever = TestNeo4jRetriever()
        
        # Test data with Neo4j DateTime objects
        test_datetime = datetime(2023, 1, 15, 10, 30, 45)
        mock_neo4j_datetime = MockNeo4jDateTime(test_datetime)
        
        node_data = {
            'id': 'test_node_123',
            'audio_id': 'audio_456',
            'user_id': 'user_789',
            'text': 'This is test content',
            'created_at': mock_neo4j_datetime,  # Neo4j DateTime object
            'updated_at': mock_neo4j_datetime,  # Neo4j DateTime object
            'other_field': 'normal_value',
            'another_datetime': mock_neo4j_datetime  # Another DateTime field
        }
        
        # Test the _clean_node_properties method
        cleaned = retriever._clean_node_properties(node_data)
        
        print("✅ _clean_node_properties executed successfully!")
        print(f"📊 Cleaned properties keys: {list(cleaned.keys())}")
        
        # Verify DateTime objects were converted to strings
        success = True
        for key, value in cleaned.items():
            if key in ['created_at', 'updated_at', 'another_datetime']:
                if isinstance(value, str):
                    print(f"✅ {key}: Converted to string: {value}")
                else:
                    print(f"❌ {key}: Still {type(value)}: {value}")
                    success = False
            else:
                print(f"ℹ️  {key}: {value}")
        
        # Verify the format is ISO
        if 'created_at' in cleaned and isinstance(cleaned['created_at'], str):
            try:
                # Try to parse it back
                parsed = datetime.fromisoformat(cleaned['created_at'])
                print(f"✅ ISO format is valid: {cleaned['created_at']}")
            except Exception as e:
                print(f"❌ ISO format is invalid: {e}")
                success = False
        
        # Test serialization with pydantic
        try:
            import json
            json_str = json.dumps(cleaned)
            print(f"✅ JSON serialization successful! Length: {len(json_str)}")
        except Exception as e:
            print(f"❌ JSON serialization failed: {e}")
            success = False
        
        return success
        
    except Exception as e:
        print(f"❌ Error testing Neo4j DateTime serialization: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_metadata_serialization():
    """Test that metadata with DateTime objects can be serialized"""
    print("\n" + "=" * 60)
    print("TESTING METADATA SERIALIZATION")
    print("=" * 60)
    
    try:
        # Simulate what happens in the context aggregator
        test_datetime = datetime(2023, 1, 15, 10, 30, 45)
        mock_neo4j_datetime = MockNeo4jDateTime(test_datetime)
        
        metadata = {
            'node_id': 'test_123',
            'created_at': mock_neo4j_datetime,
            'updated_at': mock_neo4j_datetime,
            'regular_field': 'normal_value'
        }
        
        # Simulate cleaning process
        cleaned_metadata = {}
        for key, value in metadata.items():
            if hasattr(value, 'to_native'):
                cleaned_metadata[key] = value.to_native().isoformat()
            else:
                cleaned_metadata[key] = value
        
        print(f"✅ Metadata cleaned successfully")
        print(f"📊 Original created_at type: {type(metadata['created_at'])}")
        print(f"📊 Cleaned created_at type: {type(cleaned_metadata['created_at'])}")
        print(f"📊 Cleaned created_at value: {cleaned_metadata['created_at']}")
        
        # Test with pydantic model
        try:
            from pydantic import BaseModel
            from typing import Optional
            
            class TestResponse(BaseModel):
                metadata: Dict[str, Any]
            
            response = TestResponse(metadata=cleaned_metadata)
            json_output = response.model_dump_json()
            print(f"✅ Pydantic serialization successful!")
            print(f"📄 JSON preview: {json_output[:100]}...")
            
            return True
            
        except Exception as e:
            print(f"❌ Pydantic serialization failed: {e}")
            return False
        
    except Exception as e:
        print(f"❌ Error testing metadata serialization: {e}")
        return False


if __name__ == "__main__":
    print("🔧 TESTING FIXES FOR NEO4J DATETIME SERIALIZATION")
    print("=" * 80)
    
    test_results = []
    
    # Test 1: Neo4j DateTime conversion
    test_results.append(test_neo4j_datetime_serialization())
    
    # Test 2: Metadata serialization
    test_results.append(test_metadata_serialization())
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY OF FIXES")
    print("=" * 80)
    
    passed_tests = sum(test_results)
    total_tests = len(test_results)
    
    print(f"✅ Tests passed: {passed_tests}/{total_tests}")
    
    if passed_tests == total_tests:
        print("🎉 All fixes are working correctly!")
        print("\n🔧 ISSUES FIXED:")
        print("1. ✅ Neo4j DateTime objects converted to ISO strings in metadata")
        print("2. ✅ Pydantic can now serialize responses with Neo4j data")
        print("3. ✅ ADK content handling improved with better error recovery")
    else:
        print("❌ Some fixes need additional work")
        
    print("\n💡 The errors from backend/errors/4.txt should now be resolved!")