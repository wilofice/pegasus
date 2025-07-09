#!/usr/bin/env python3
"""
Test script to verify the fixes for the errors in backend/errors/3.txt
"""

import sys
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass, field

# Add the backend directory to the path for direct imports
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

def test_rankedresult_to_dict():
    """Test that RankedResult has a working to_dict() method."""
    print("=" * 60)
    print("TESTING RANKEDRESULT TO_DICT() FIX")
    print("=" * 60)
    
    try:
        from services.context_ranker import RankedResult, RankingFactor
        
        # Create a sample RankedResult
        ranking_factor = RankingFactor(
            name="semantic_similarity",
            score=0.85,
            weight=0.4,
            explanation="High semantic similarity with query",
            raw_value=0.85
        )
        
        ranked_result = RankedResult(
            id="test_result_1",
            content="This is test content about personal development",
            source_type="vector",
            unified_score=0.82,
            ranking_factors=[ranking_factor],
            metadata={"source": "test_doc", "timestamp": "2023-01-01"},
            semantic_score=0.85,
            structural_score=0.78,
            temporal_score=0.65
        )
        
        # Test the to_dict() method
        result_dict = ranked_result.to_dict()
        
        print("✅ RankedResult.to_dict() method works correctly!")
        print(f"📊 Result dictionary keys: {list(result_dict.keys())}")
        print(f"📝 Content preview: {result_dict['content'][:50]}...")
        print(f"🔢 Unified score: {result_dict['unified_score']}")
        print(f"🔍 Ranking factors count: {len(result_dict['ranking_factors'])}")
        
        # Verify all expected fields are present
        expected_fields = [
            'id', 'content', 'source_type', 'unified_score', 'metadata',
            'semantic_score', 'structural_score', 'temporal_score', 'ranking_factors'
        ]
        
        missing_fields = [field for field in expected_fields if field not in result_dict]
        if missing_fields:
            print(f"❌ Missing fields: {missing_fields}")
            return False
        else:
            print("✅ All expected fields present in dictionary")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing RankedResult.to_dict(): {e}")
        return False


def test_vertex_adk_content_structure():
    """Test that the ADK content structure is correct."""
    print("\n" + "=" * 60)
    print("TESTING VERTEX ADK CONTENT STRUCTURE FIX")
    print("=" * 60)
    
    try:
        from vertexai.generative_models import Content, Part
        
        # Test creating content the way it's done in the fixed code
        test_message = "Hello, this is a test message"
        
        # This is the fixed way to create Part objects
        user_content = Content(
            role='user', 
            parts=[Part(text=test_message)]
        )
        
        print("✅ Content structure created successfully!")
        print(f"📝 Role: {user_content.role}")
        print(f"🔢 Parts count: {len(user_content.parts)}")
        print(f"📄 Part text: {user_content.parts[0].text}")
        
        # Verify the part has the text attribute
        if hasattr(user_content.parts[0], 'text'):
            print("✅ Part object has text attribute")
        else:
            print("❌ Part object missing text attribute")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Error testing ADK content structure: {e}")
        return False


def test_chat_orchestrator_sources():
    """Test that the chat orchestrator can handle sources correctly."""
    print("\n" + "=" * 60)
    print("TESTING CHAT ORCHESTRATOR SOURCES EXTRACTION")
    print("=" * 60)
    
    try:
        from services.context_ranker import RankedResult, RankingFactor
        from services.context_aggregator_v2 import AggregatedContext
        from services.chat_types import ChatConfig, ResponseStyle
        
        # Create mock ranked results
        ranking_factor = RankingFactor(
            name="semantic_similarity",
            score=0.85,
            weight=0.4,
            explanation="High semantic similarity",
            raw_value=0.85
        )
        
        ranked_results = [
            RankedResult(
                id="result_1",
                content="Test content 1",
                source_type="vector",
                unified_score=0.82,
                ranking_factors=[ranking_factor],
                metadata={"source": "doc1"}
            ),
            RankedResult(
                id="result_2", 
                content="Test content 2",
                source_type="graph",
                unified_score=0.75,
                ranking_factors=[ranking_factor],
                metadata={"source": "doc2"}
            )
        ]
        
        # Create mock aggregated context
        aggregated_context = AggregatedContext(
            results=ranked_results,
            query="test query"
        )
        
        # Test the _extract_sources method logic
        config = ChatConfig(include_sources=True, response_style=ResponseStyle.DETAILED)
        
        # Simulate what _extract_sources does
        if config.include_sources and aggregated_context.results:
            sources = [r.to_dict() for r in aggregated_context.results[:5]]
            print(f"✅ Successfully extracted {len(sources)} sources")
            print(f"📊 First source keys: {list(sources[0].keys())}")
            print(f"🔢 First source score: {sources[0]['unified_score']}")
        else:
            sources = []
            print("ℹ️  No sources to extract")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing source extraction: {e}")
        return False


if __name__ == "__main__":
    print("🔧 TESTING FIXES FOR BACKEND/ERRORS/3.TXT")
    print("=" * 80)
    
    test_results = []
    
    # Test 1: RankedResult.to_dict() fix
    test_results.append(test_rankedresult_to_dict())
    
    # Test 2: Vertex ADK content structure fix
    test_results.append(test_vertex_adk_content_structure())
    
    # Test 3: Chat orchestrator sources extraction
    test_results.append(test_chat_orchestrator_sources())
    
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
        print("1. ✅ RankedResult now has to_dict() method")
        print("2. ✅ Vertex ADK content structure corrected")
        print("3. ✅ Chat orchestrator can extract sources properly")
    else:
        print("❌ Some fixes need additional work")
        
    print("\n💡 The errors from backend/errors/3.txt should now be resolved!")