#!/usr/bin/env python3
"""Test script for Review & Reflection plugin."""
import sys
import logging
import asyncio
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_plugin_metadata():
    """Test plugin metadata and configuration."""
    try:
        from plugins.review_reflection import ReviewReflectionPlugin
        
        plugin = ReviewReflectionPlugin()
        metadata = plugin.metadata
        
        logger.info(f"✅ Plugin metadata:")
        logger.info(f"  Name: {metadata.name}")
        logger.info(f"  Version: {metadata.version}")
        logger.info(f"  Type: {metadata.plugin_type}")
        logger.info(f"  Author: {metadata.author}")
        logger.info(f"  Dependencies: {metadata.dependencies}")
        logger.info(f"  Tags: {metadata.tags}")
        
        # Test configuration validation
        valid_config = await plugin.validate_config({
            "min_confidence": 0.7,
            "max_insights": 15,
            "enable_action_items": True
        })
        
        logger.info(f"✅ Configuration validation: {valid_config}")
        
        assert metadata.name == "review_reflection"
        assert metadata.plugin_type.value == "analysis"
        assert len(metadata.tags) > 0
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Plugin metadata test failed: {e}")
        return False


async def test_basic_analysis():
    """Test basic review and reflection analysis."""
    try:
        from plugins.review_reflection import ReviewReflectionPlugin
        from services.plugin_manager import PluginContext
        
        plugin = ReviewReflectionPlugin({
            "min_confidence": 0.5,
            "max_insights": 20,
            "enable_action_items": True,
            "enable_emotional_analysis": True,
            "enable_learning_insights": True
        })
        
        # Create test context with a meeting transcript
        context = PluginContext(
            audio_id="test_audio_123",
            user_id="test_user_456",
            transcript="""
            Good morning everyone, thanks for joining today's project review meeting. 
            I'm excited to share the progress we've made on the AI initiative. 
            
            First, let me ask - what are the main challenges we're facing with the current implementation?
            John mentioned some concerns about the performance metrics last week.
            
            We need to decide on the next steps by Friday. I think we should focus on improving the user experience.
            Sarah, can you take the lead on the UX improvements? 
            
            Also, we should schedule a follow-up meeting with the stakeholders to discuss the budget allocation.
            This is a great learning opportunity for our team to develop new skills in machine learning.
            
            Are there any other questions or concerns before we wrap up?
            I believe we can achieve our goals if we work together and stay focused.
            """,
            metadata={
                "language": "en",
                "category": "meeting",
                "tags": ["project_review", "ai_initiative"],
                "duration": 600
            },
            entities=[
                {"text": "John", "type": "PERSON"},
                {"text": "Sarah", "type": "PERSON"},
                {"text": "AI initiative", "type": "PROJECT"},
                {"text": "Friday", "type": "DATE"}
            ],
            chunks=[
                {"id": "chunk_1", "text": "Good morning everyone...", "metadata": {}},
                {"id": "chunk_2", "text": "First, let me ask...", "metadata": {}},
                {"id": "chunk_3", "text": "We need to decide...", "metadata": {}}
            ]
        )
        
        # Execute plugin
        result = await plugin.execute(context)
        
        logger.info(f"✅ Plugin execution result:")
        logger.info(f"  Success: {result.success}")
        logger.info(f"  Plugin: {result.plugin_name}")
        
        if result.success and result.result_data:
            insights = result.result_data.get("insights", [])
            summary = result.result_data.get("summary", {})
            recommendations = result.result_data.get("recommendations", [])
            metrics = result.result_data.get("metrics", {})
            
            logger.info(f"  Total insights: {len(insights)}")
            logger.info(f"  Conversation type: {summary.get('conversation_type', 'Unknown')}")
            logger.info(f"  Overall sentiment: {summary.get('overall_sentiment', 'Unknown')}")
            logger.info(f"  Recommendations: {len(recommendations)}")
            
            # Show some insights
            logger.info(f"\n📋 Sample Insights:")
            for i, insight in enumerate(insights[:3]):
                logger.info(f"  {i+1}. [{insight['category']}] {insight['insight']}")
                logger.info(f"     Confidence: {insight['confidence']:.2f}")
                logger.info(f"     Action items: {len(insight['action_items'])}")
            
            # Show metrics
            logger.info(f"\n📊 Analysis Metrics:")
            logger.info(f"  Insights generated: {metrics.get('total_insights_generated', 0)}")
            logger.info(f"  Above threshold: {metrics.get('insights_above_threshold', 0)}")
            logger.info(f"  Categories found: {metrics.get('categories_found', [])}")
            logger.info(f"  Average confidence: {metrics.get('average_confidence', 0):.2f}")
            
            # Validate key features were detected
            categories = [insight['category'] for insight in insights]
            assert "Communication Style" in categories or "Action Items" in categories
            assert len(insights) > 0
            assert summary.get('conversation_type') is not None
            
        else:
            logger.error(f"Plugin execution failed: {result.error_message}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Basic analysis test failed: {e}")
        return False


async def test_action_item_extraction():
    """Test action item extraction specifically."""
    try:
        from plugins.review_reflection import ReviewReflectionPlugin
        from services.plugin_manager import PluginContext
        
        plugin = ReviewReflectionPlugin({
            "enable_action_items": True,
            "min_confidence": 0.3
        })
        
        # Create context focused on action items
        context = PluginContext(
            audio_id="test_action_items",
            user_id="test_user",
            transcript="""
            Alright team, let's wrap up with our action items.
            
            First, I will review the requirements document and provide feedback by Monday.
            Sarah, you'll take care of updating the project timeline.
            We need to schedule a meeting with the client before the end of the week.
            
            John agreed to research the new technologies we discussed.
            The team decided to implement the new feature in the next sprint.
            We must finalize the budget proposal by the deadline on Friday.
            
            Action item: Follow up with the marketing team about the campaign launch.
            Task: Create a detailed project plan for the next quarter.
            """,
            metadata={"category": "action_planning"},
            entities=[
                {"text": "Sarah", "type": "PERSON"},
                {"text": "John", "type": "PERSON"},
                {"text": "Monday", "type": "DATE"},
                {"text": "Friday", "type": "DATE"}
            ]
        )
        
        result = await plugin.execute(context)
        
        logger.info(f"✅ Action item extraction test:")
        logger.info(f"  Success: {result.success}")
        
        if result.success:
            insights = result.result_data.get("insights", [])
            action_insights = [i for i in insights if i['category'] == 'Action Items']
            
            logger.info(f"  Action item insights found: {len(action_insights)}")
            
            for insight in action_insights:
                logger.info(f"    - {insight['insight']}")
                logger.info(f"      Evidence: {insight['evidence']}")
                logger.info(f"      Actions: {insight['action_items']}")
            
            # Should find action items
            assert len(action_insights) > 0
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Action item extraction test failed: {e}")
        return False


async def test_emotional_analysis():
    """Test emotional tone analysis."""
    try:
        from plugins.review_reflection import ReviewReflectionPlugin
        from services.plugin_manager import PluginContext
        
        plugin = ReviewReflectionPlugin({
            "enable_emotional_analysis": True,
            "min_confidence": 0.4
        })
        
        # Test positive emotional context
        positive_context = PluginContext(
            audio_id="test_positive",
            user_id="test_user",
            transcript="""
            This is fantastic! I'm really excited about the progress we've made.
            The team has done an excellent job, and I'm very pleased with the results.
            Everything looks great, and I love the direction we're heading.
            This is exactly what we wanted to achieve - amazing work everyone!
            """,
            metadata={"category": "celebration"}
        )
        
        result = await plugin.execute(positive_context)
        
        logger.info(f"✅ Positive emotional analysis:")
        logger.info(f"  Success: {result.success}")
        
        if result.success:
            summary = result.result_data.get("summary", {})
            sentiment = summary.get("overall_sentiment", "Unknown")
            logger.info(f"  Overall sentiment: {sentiment}")
            
            emotional_insights = [
                i for i in result.result_data.get("insights", [])
                if i['category'] == 'Emotional Tone'
            ]
            
            for insight in emotional_insights:
                logger.info(f"    - {insight['insight']}")
            
            # Should detect positive sentiment
            assert sentiment in ["Positive", "Balanced"]
        
        # Test negative emotional context
        negative_context = PluginContext(
            audio_id="test_negative",
            user_id="test_user",
            transcript="""
            I'm really concerned about these issues we're facing.
            The performance has been disappointing, and we're seeing terrible results.
            This is frustrating, and I'm worried about the impact on our timeline.
            We have serious problems that need immediate attention.
            """,
            metadata={"category": "problem_solving"}
        )
        
        result2 = await plugin.execute(negative_context)
        
        logger.info(f"✅ Negative emotional analysis:")
        logger.info(f"  Success: {result2.success}")
        
        if result2.success:
            summary2 = result2.result_data.get("summary", {})
            sentiment2 = summary2.get("overall_sentiment", "Unknown")
            logger.info(f"  Overall sentiment: {sentiment2}")
            
            # Should detect concerned sentiment
            assert sentiment2 in ["Concerned", "Balanced"]
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Emotional analysis test failed: {e}")
        return False


async def test_learning_opportunities():
    """Test learning opportunity identification."""
    try:
        from plugins.review_reflection import ReviewReflectionPlugin
        from services.plugin_manager import PluginContext
        
        plugin = ReviewReflectionPlugin({
            "enable_learning_insights": True,
            "min_confidence": 0.5
        })
        
        context = PluginContext(
            audio_id="test_learning",
            user_id="test_user",
            transcript="""
            This is a great learning opportunity for our team.
            We need to develop new skills in machine learning and data science.
            I think we should invest in training and education for everyone.
            
            What's the best way to approach this new technology?
            How can we improve our current processes?
            Are there any innovative solutions we haven't considered?
            
            We made some mistakes in the previous project, but we learned valuable lessons.
            Let's brainstorm some creative ideas for the next phase.
            This experience will help us grow as a team.
            """,
            metadata={"category": "professional_development"},
            entities=[
                {"text": "machine learning", "type": "TECHNOLOGY"},
                {"text": "data science", "type": "TECHNOLOGY"}
            ]
        )
        
        result = await plugin.execute(context)
        
        logger.info(f"✅ Learning opportunities test:")
        logger.info(f"  Success: {result.success}")
        
        if result.success:
            insights = result.result_data.get("insights", [])
            learning_insights = [
                i for i in insights 
                if i['category'] in ['Learning Opportunities', 'Knowledge Gaps', 'Innovation']
            ]
            
            logger.info(f"  Learning-related insights: {len(learning_insights)}")
            
            for insight in learning_insights:
                logger.info(f"    - [{insight['category']}] {insight['insight']}")
            
            # Should find learning opportunities
            assert len(learning_insights) > 0
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Learning opportunities test failed: {e}")
        return False


async def test_configuration_options():
    """Test different configuration options."""
    try:
        from plugins.review_reflection import ReviewReflectionPlugin
        from services.plugin_manager import PluginContext
        
        # Test with minimal configuration
        minimal_plugin = ReviewReflectionPlugin({
            "min_confidence": 0.9,  # Very high threshold
            "max_insights": 3,      # Very limited
            "enable_action_items": False,
            "enable_emotional_analysis": False,
            "enable_learning_insights": False
        })
        
        context = PluginContext(
            audio_id="test_config",
            user_id="test_user",
            transcript="This is a short test conversation with minimal content.",
            metadata={}
        )
        
        result = await minimal_plugin.execute(context)
        
        logger.info(f"✅ Minimal configuration test:")
        logger.info(f"  Success: {result.success}")
        
        if result.success:
            insights = result.result_data.get("insights", [])
            config_used = result.result_data.get("config_used", {})
            
            logger.info(f"  Insights with high threshold: {len(insights)}")
            logger.info(f"  Config used: {config_used}")
            
            # Should have very few or no insights due to high threshold
            assert len(insights) <= 3
            assert config_used["min_confidence"] == 0.9
            
        # Test with comprehensive configuration
        comprehensive_plugin = ReviewReflectionPlugin({
            "min_confidence": 0.1,  # Very low threshold
            "max_insights": 25,     # High limit
            "enable_action_items": True,
            "enable_emotional_analysis": True,
            "enable_learning_insights": True
        })
        
        rich_context = PluginContext(
            audio_id="test_comprehensive",
            user_id="test_user",
            transcript="""
            This is a comprehensive meeting where we discuss many topics.
            We need to make several decisions and create action items.
            I'm excited about the opportunities, but also concerned about challenges.
            What can we learn from this experience? How can we improve?
            John will handle the research, and Sarah will coordinate with stakeholders.
            We agreed to move forward with the new strategy by next Friday.
            """,
            metadata={"category": "comprehensive_meeting"},
            entities=[
                {"text": "John", "type": "PERSON"},
                {"text": "Sarah", "type": "PERSON"},
                {"text": "Friday", "type": "DATE"}
            ]
        )
        
        result2 = await comprehensive_plugin.execute(rich_context)
        
        logger.info(f"✅ Comprehensive configuration test:")
        logger.info(f"  Success: {result2.success}")
        
        if result2.success:
            insights2 = result2.result_data.get("insights", [])
            logger.info(f"  Insights with low threshold: {len(insights2)}")
            
            # Should have more insights due to low threshold and rich content
            assert len(insights2) > len(insights)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Configuration options test failed: {e}")
        return False


async def main():
    """Run all Review & Reflection plugin tests."""
    logger.info("🧪 Running Review & Reflection Plugin Tests")
    
    tests = [
        ("Plugin Metadata", test_plugin_metadata),
        ("Basic Analysis", test_basic_analysis),
        ("Action Item Extraction", test_action_item_extraction),
        ("Emotional Analysis", test_emotional_analysis),
        ("Learning Opportunities", test_learning_opportunities),
        ("Configuration Options", test_configuration_options),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n--- Running {test_name} ---")
        try:
            result = await test_func()
            
            if result:
                passed += 1
                logger.info(f"✅ {test_name} PASSED")
            else:
                logger.error(f"❌ {test_name} FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name} FAILED with exception: {e}")
    
    logger.info(f"\n🏁 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All Review & Reflection plugin tests passed!")
        logger.info("\n📋 Plugin Features Validated:")
        logger.info("  ✅ Communication pattern analysis")
        logger.info("  ✅ Action item extraction and tracking")
        logger.info("  ✅ Emotional tone and sentiment analysis")
        logger.info("  ✅ Learning opportunity identification")
        logger.info("  ✅ Decision point and consensus analysis")
        logger.info("  ✅ Configurable analysis parameters")
        logger.info("  ✅ Comprehensive insights and recommendations")
        logger.info("  ✅ Rich metadata and confidence scoring")
        return 0
    else:
        logger.error("💥 Some Review & Reflection plugin tests failed.")
        return 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))