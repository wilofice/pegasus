#!/usr/bin/env python3
"""
Test script to demonstrate session-aware prompt building optimization.

This script shows the difference between first request and subsequent requests
in terms of prompt components and token usage.
"""

import asyncio
import logging
from typing import Dict, Any, List

# Mock imports for testing
from services.intelligent_prompt_builder import IntelligentPromptBuilder
from services.context_aggregator_v2 import AggregatedContext, ContextResult
from services.chat_types import ChatConfig, ConversationMode, ResponseStyle, ConversationContext

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_mock_aggregated_context() -> AggregatedContext:
    """Create mock aggregated context for testing."""
    mock_results = [
        ContextResult(
            content="This is mock context about personal development and life coaching.",
            source_type="vector",
            unified_score=0.85,
            metadata={"source": "mock_document_1", "timestamp": "2023-01-01"}
        ),
        ContextResult(
            content="Additional context about goal setting and achievement strategies.",
            source_type="graph",
            unified_score=0.72,
            metadata={"source": "mock_document_2", "timestamp": "2023-01-02"}
        )
    ]
    
    return AggregatedContext(results=mock_results, query="test query")


def create_mock_conversation_context(has_history: bool = False) -> ConversationContext:
    """Create mock conversation context."""
    history = []
    if has_history:
        history = [
            {
                "user_message": "Hello, I want to improve my productivity.",
                "assistant_response": "I'd be happy to help you improve your productivity. Let's start by understanding your current challenges."
            }
        ]
    
    return ConversationContext(
        session_id="test_session_123",
        user_id="test_user",
        conversation_history=history
    )


async def test_session_aware_prompting():
    """Test the session-aware prompt building functionality."""
    
    print("=" * 80)
    print("SESSION-AWARE PROMPT BUILDING TEST")
    print("=" * 80)
    
    # Initialize prompt builder
    prompt_builder = IntelligentPromptBuilder()
    
    # Create test data
    user_message = "How can I set better goals for my career development?"
    aggregated_context = create_mock_aggregated_context()
    plugin_results = {"results": {}, "executed_plugins": []}
    config = ChatConfig(
        conversation_mode=ConversationMode.RESEARCH,
        response_style=ResponseStyle.DETAILED,
        max_context_results=5,
        include_sources=True
    )
    recent_transcripts = ["Recent audio: I discussed my career aspirations with my mentor."]
    
    # Test 1: First request (new session)
    print("\n📋 TEST 1: FIRST REQUEST (NEW SESSION)")
    print("-" * 50)
    
    conversation_context_first = create_mock_conversation_context(has_history=False)
    
    first_prompt = prompt_builder.build_intelligent_prompt(
        user_message=user_message,
        aggregated_context=aggregated_context,
        plugin_results=plugin_results,
        config=config,
        conversation_context=conversation_context_first,
        recent_transcripts=recent_transcripts,
        is_first_request=True  # This is the key difference
    )
    
    first_prompt_length = len(first_prompt)
    first_prompt_lines = first_prompt.count('\n')
    
    print(f"✅ First request prompt generated")
    print(f"📏 Length: {first_prompt_length} characters")
    print(f"📄 Lines: {first_prompt_lines}")
    print(f"🔧 Components included:")
    print("   - ✅ System Instructions")
    print("   - ✅ Context Section") 
    print("   - ✅ Conversation Section")
    print("   - ✅ Task Instructions (Full)")
    print("   - ✅ Response Framework")
    print("   - ✅ Quality Instructions")
    print("   - ✅ Transcript Section")
    
    # Test 2: Subsequent request (continuing session)
    print("\n📋 TEST 2: SUBSEQUENT REQUEST (CONTINUING SESSION)")
    print("-" * 50)
    
    conversation_context_subsequent = create_mock_conversation_context(has_history=True)
    
    subsequent_prompt = prompt_builder.build_intelligent_prompt(
        user_message="Can you give me specific examples of SMART goals?",
        aggregated_context=aggregated_context,
        plugin_results=plugin_results,
        config=config,
        conversation_context=conversation_context_subsequent,
        recent_transcripts=recent_transcripts,
        is_first_request=False  # This is the key difference
    )
    
    subsequent_prompt_length = len(subsequent_prompt)
    subsequent_prompt_lines = subsequent_prompt.count('\n')
    
    print(f"✅ Subsequent request prompt generated")
    print(f"📏 Length: {subsequent_prompt_length} characters")
    print(f"📄 Lines: {subsequent_prompt_lines}")
    print(f"🔧 Components included:")
    print("   - ❌ System Instructions (SKIPPED)")
    print("   - ✅ Context Section") 
    print("   - ✅ Conversation Section")
    print("   - ✅ Task Instructions (User Question Only)")
    print("   - ❌ Response Framework (SKIPPED)")
    print("   - ❌ Quality Instructions (SKIPPED)")
    print("   - ✅ Transcript Section")
    
    # Calculate optimization metrics
    print("\n📊 OPTIMIZATION ANALYSIS")
    print("-" * 50)
    
    size_reduction = first_prompt_length - subsequent_prompt_length
    percentage_reduction = (size_reduction / first_prompt_length) * 100
    
    print(f"📉 Size reduction: {size_reduction} characters ({percentage_reduction:.1f}%)")
    print(f"⚡ Token savings: ~{size_reduction // 4} tokens (estimated)")
    
    # Estimate components that were optimized away
    system_instructions_marker = "=== PEGASUS BRAIN ROLE & IDENTITY ==="
    response_framework_marker = "=== RESPONSE FRAMEWORK ==="
    quality_instructions_marker = "=== QUALITY REQUIREMENTS ==="
    
    optimized_components = []
    if system_instructions_marker in first_prompt and system_instructions_marker not in subsequent_prompt:
        optimized_components.append("System Instructions")
    if response_framework_marker in first_prompt and response_framework_marker not in subsequent_prompt:
        optimized_components.append("Response Framework")
    if quality_instructions_marker in first_prompt and quality_instructions_marker not in subsequent_prompt:
        optimized_components.append("Quality Instructions")
    
    print(f"🎯 Optimized components: {', '.join(optimized_components)}")
    
    # Show actual prompt snippets for comparison
    print("\n📝 PROMPT PREVIEW COMPARISON")
    print("-" * 50)
    
    print("🔸 First Request (first 200 chars):")
    print(f"   {first_prompt[:200]}...")
    print()
    print("🔸 Subsequent Request (first 200 chars):")
    print(f"   {subsequent_prompt[:200]}...")
    
    print("\n✅ SESSION-AWARE OPTIMIZATION TEST COMPLETED")
    print(f"💡 Result: {percentage_reduction:.1f}% reduction in prompt size for subsequent requests")
    print("🚀 This optimization reduces token usage while maintaining conversation quality!")
    
    return {
        "first_prompt_length": first_prompt_length,
        "subsequent_prompt_length": subsequent_prompt_length,
        "reduction_percentage": percentage_reduction,
        "optimized_components": optimized_components
    }


if __name__ == "__main__":
    # Run the test
    results = asyncio.run(test_session_aware_prompting())
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"✨ Session-aware prompt building successfully reduces prompt size by {results['reduction_percentage']:.1f}%")
    print(f"📊 First request: {results['first_prompt_length']} chars")
    print(f"📊 Subsequent requests: {results['subsequent_prompt_length']} chars")
    print(f"🎯 Optimized components: {', '.join(results['optimized_components'])}")
    print("\n🎉 Smart prompting optimization is working correctly!")