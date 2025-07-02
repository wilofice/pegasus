"""Review & Reflection plugin for analyzing conversation insights."""
import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from services.plugin_manager import BasePlugin, PluginMetadata, PluginContext, PluginResult, PluginType

logger = logging.getLogger(__name__)


@dataclass
class ReflectionInsight:
    """A single reflection insight."""
    category: str
    insight: str
    confidence: float
    evidence: List[str]
    action_items: List[str]


class ReviewReflectionPlugin(BasePlugin):
    """Plugin that generates review insights and reflections from conversations."""
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="review_reflection",
            version="1.0.0",
            description="Analyzes conversations to generate insights, reflections, and action items",
            author="Pegasus Brain Team",
            plugin_type=PluginType.ANALYSIS,
            dependencies=[],
            tags=["review", "reflection", "insights", "analysis", "action_items"],
            config_schema={
                "type": "object",
                "properties": {
                    "min_confidence": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "default": 0.6,
                        "description": "Minimum confidence threshold for insights"
                    },
                    "max_insights": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 20,
                        "default": 10,
                        "description": "Maximum number of insights to generate"
                    },
                    "enable_action_items": {
                        "type": "boolean",
                        "default": True,
                        "description": "Whether to extract action items"
                    },
                    "enable_emotional_analysis": {
                        "type": "boolean", 
                        "default": True,
                        "description": "Whether to perform emotional analysis"
                    },
                    "enable_learning_insights": {
                        "type": "boolean",
                        "default": True,
                        "description": "Whether to generate learning insights"
                    }
                }
            }
        )
    
    async def execute(self, context: PluginContext) -> PluginResult:
        """Execute the review and reflection analysis."""
        try:
            start_time = datetime.now()
            
            # Get configuration
            min_confidence = self.get_config_value("min_confidence", 0.6)
            max_insights = self.get_config_value("max_insights", 10)
            enable_action_items = self.get_config_value("enable_action_items", True)
            enable_emotional_analysis = self.get_config_value("enable_emotional_analysis", True)
            enable_learning_insights = self.get_config_value("enable_learning_insights", True)
            
            transcript = context.transcript
            metadata = context.metadata
            entities = context.entities or []
            chunks = context.chunks or []
            
            insights = []
            
            # 1. Communication Patterns Analysis
            communication_insights = self._analyze_communication_patterns(transcript, entities)
            insights.extend(communication_insights)
            
            # 2. Content Structure Analysis
            structure_insights = self._analyze_content_structure(transcript, chunks)
            insights.extend(structure_insights)
            
            # 3. Action Items Extraction
            if enable_action_items:
                action_insights = self._extract_action_items(transcript, entities)
                insights.extend(action_insights)
            
            # 4. Emotional Tone Analysis
            if enable_emotional_analysis:
                emotional_insights = self._analyze_emotional_tone(transcript)
                insights.extend(emotional_insights)
            
            # 5. Learning and Development Insights
            if enable_learning_insights:
                learning_insights = self._analyze_learning_opportunities(transcript, entities)
                insights.extend(learning_insights)
            
            # 6. Decision Points Analysis
            decision_insights = self._analyze_decision_points(transcript, entities)
            insights.extend(decision_insights)
            
            # Filter by confidence and limit results
            filtered_insights = [
                insight for insight in insights 
                if insight.confidence >= min_confidence
            ]
            
            # Sort by confidence and limit
            filtered_insights.sort(key=lambda x: x.confidence, reverse=True)
            filtered_insights = filtered_insights[:max_insights]
            
            # Generate summary and recommendations
            summary = self._generate_summary(filtered_insights, transcript, metadata)
            recommendations = self._generate_recommendations(filtered_insights, metadata)
            
            # Calculate metrics
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            result_data = {
                "insights": [
                    {
                        "category": insight.category,
                        "insight": insight.insight,
                        "confidence": insight.confidence,
                        "evidence": insight.evidence,
                        "action_items": insight.action_items
                    }
                    for insight in filtered_insights
                ],
                "summary": summary,
                "recommendations": recommendations,
                "metrics": {
                    "total_insights_generated": len(insights),
                    "insights_above_threshold": len(filtered_insights),
                    "confidence_threshold": min_confidence,
                    "average_confidence": sum(i.confidence for i in filtered_insights) / len(filtered_insights) if filtered_insights else 0,
                    "categories_found": list(set(i.category for i in filtered_insights)),
                    "transcript_length": len(transcript),
                    "entities_analyzed": len(entities),
                    "chunks_analyzed": len(chunks)
                },
                "config_used": {
                    "min_confidence": min_confidence,
                    "max_insights": max_insights,
                    "enable_action_items": enable_action_items,
                    "enable_emotional_analysis": enable_emotional_analysis,
                    "enable_learning_insights": enable_learning_insights
                }
            }
            
            return PluginResult(
                plugin_name=self.metadata.name,
                success=True,
                result_data=result_data,
                metadata={
                    "analysis_type": "review_reflection",
                    "insights_count": len(filtered_insights),
                    "processing_time_ms": execution_time
                }
            )
            
        except Exception as e:
            logger.error(f"Error in review reflection analysis: {e}")
            return PluginResult(
                plugin_name=self.metadata.name,
                success=False,
                error_message=f"Review reflection analysis failed: {str(e)}"
            )
    
    def _analyze_communication_patterns(self, transcript: str, entities: List[Dict]) -> List[ReflectionInsight]:
        """Analyze communication patterns in the conversation."""
        insights = []
        
        # Analyze question patterns
        question_count = len(re.findall(r'\?', transcript))
        total_sentences = len(re.findall(r'[.!?]', transcript))
        
        if total_sentences > 0:
            question_ratio = question_count / total_sentences
            
            if question_ratio > 0.3:
                insights.append(ReflectionInsight(
                    category="Communication Style",
                    insight="High level of inquiry and curiosity demonstrated through frequent questioning",
                    confidence=0.8,
                    evidence=[f"Asked {question_count} questions out of {total_sentences} statements ({question_ratio:.1%})"],
                    action_items=["Consider following up on unanswered questions", "Document key questions for future reference"]
                ))
            elif question_ratio < 0.1:
                insights.append(ReflectionInsight(
                    category="Communication Style", 
                    insight="Conversation was more declarative with limited questioning",
                    confidence=0.7,
                    evidence=[f"Only {question_count} questions out of {total_sentences} statements ({question_ratio:.1%})"],
                    action_items=["Consider asking more probing questions in future discussions"]
                ))
        
        # Analyze entity diversity (people, organizations, concepts)
        person_entities = [e for e in entities if e.get('type') == 'PERSON']
        org_entities = [e for e in entities if e.get('type') == 'ORG']
        
        if len(person_entities) > 3:
            insights.append(ReflectionInsight(
                category="Stakeholder Engagement",
                insight=f"Multiple stakeholders were discussed ({len(person_entities)} people mentioned)",
                confidence=0.75,
                evidence=[f"People mentioned: {', '.join([e.get('text', '') for e in person_entities[:5]])}"],
                action_items=["Consider reaching out to key stakeholders mentioned", "Map stakeholder relationships"]
            ))
        
        if len(org_entities) > 2:
            insights.append(ReflectionInsight(
                category="Organizational Context",
                insight=f"Cross-organizational discussion involving {len(org_entities)} organizations",
                confidence=0.7,
                evidence=[f"Organizations: {', '.join([e.get('text', '') for e in org_entities[:3]])}"],
                action_items=["Consider organizational alignment and coordination needs"]
            ))
        
        return insights
    
    def _analyze_content_structure(self, transcript: str, chunks: List[Dict]) -> List[ReflectionInsight]:
        """Analyze the structure and flow of content."""
        insights = []
        
        # Analyze conversation flow
        words = transcript.split()
        if len(words) > 500:
            # Long conversation analysis
            insights.append(ReflectionInsight(
                category="Content Depth",
                insight="In-depth discussion with substantial content coverage",
                confidence=0.8,
                evidence=[f"Conversation length: {len(words)} words", f"Content organized in {len(chunks)} segments"],
                action_items=["Create detailed summary", "Identify key themes for follow-up"]
            ))
        
        # Look for transition words and structure
        transition_words = ['however', 'therefore', 'furthermore', 'in conclusion', 'first', 'second', 'finally', 'next']
        transition_count = sum(1 for word in transition_words if word in transcript.lower())
        
        if transition_count > 3:
            insights.append(ReflectionInsight(
                category="Communication Structure",
                insight="Well-structured discussion with clear transitions between topics",
                confidence=0.75,
                evidence=[f"Found {transition_count} transition indicators"],
                action_items=["Use this structure as a template for future discussions"]
            ))
        
        # Analyze topic coherence through chunks
        if len(chunks) > 1:
            # Simple coherence analysis based on chunk metadata
            coherence_score = 0.7  # Placeholder - could be enhanced with NLP
            
            insights.append(ReflectionInsight(
                category="Topic Coherence",
                insight="Conversation maintained good topical flow and coherence",
                confidence=coherence_score,
                evidence=[f"Content segmented into {len(chunks)} coherent sections"],
                action_items=["Extract main themes from each section"]
            ))
        
        return insights
    
    def _extract_action_items(self, transcript: str, entities: List[Dict]) -> List[ReflectionInsight]:
        """Extract action items and commitments from the conversation."""
        insights = []
        
        # Action item patterns
        action_patterns = [
            r'\b(?:will|shall|should|need to|must|have to|going to)\s+([^.!?]*)',
            r'\b(?:action item|task|todo|follow up|next step):\s*([^.!?]*)',
            r'\b(?:assign|responsible for|take care of|handle)\s+([^.!?]*)',
            r'\b(?:by|before|due)\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|next week|tomorrow)',
            r'\b(?:deadline|due date|timeline)\b'
        ]
        
        action_items = []
        for pattern in action_patterns:
            matches = re.findall(pattern, transcript, re.IGNORECASE)
            action_items.extend(matches)
        
        # Look for commitment language
        commitment_patterns = [
            r'\bI will\b',
            r'\bI\'ll\b', 
            r'\bwe will\b',
            r'\bwe\'ll\b',
            r'\bcommit to\b',
            r'\bagree to\b'
        ]
        
        commitment_count = sum(len(re.findall(pattern, transcript, re.IGNORECASE)) for pattern in commitment_patterns)
        
        if action_items or commitment_count > 0:
            insights.append(ReflectionInsight(
                category="Action Items",
                insight=f"Identified {len(action_items)} potential action items and {commitment_count} commitments",
                confidence=0.8 if action_items else 0.6,
                evidence=action_items[:3] + [f"{commitment_count} commitment statements found"],
                action_items=[
                    "Create formal action item list",
                    "Assign owners and deadlines",
                    "Set up follow-up tracking"
                ]
            ))
        
        # Look for decision points
        decision_patterns = [
            r'\b(?:decided|concluded|agreed|resolved)\b',
            r'\b(?:decision|choice|option)\b'
        ]
        
        decision_count = sum(len(re.findall(pattern, transcript, re.IGNORECASE)) for pattern in decision_patterns)
        
        if decision_count > 2:
            insights.append(ReflectionInsight(
                category="Decisions",
                insight=f"Multiple decisions were made during the conversation",
                confidence=0.75,
                evidence=[f"Found {decision_count} decision-related statements"],
                action_items=["Document key decisions", "Communicate decisions to stakeholders"]
            ))
        
        return insights
    
    def _analyze_emotional_tone(self, transcript: str) -> List[ReflectionInsight]:
        """Analyze emotional tone and sentiment patterns."""
        insights = []
        
        # Positive emotion words
        positive_words = ['excited', 'happy', 'pleased', 'satisfied', 'great', 'excellent', 'wonderful', 'fantastic', 'amazing', 'love', 'like', 'enjoy', 'appreciate']
        
        # Negative emotion words  
        negative_words = ['concerned', 'worried', 'frustrated', 'disappointed', 'upset', 'angry', 'sad', 'terrible', 'awful', 'hate', 'dislike', 'problem', 'issue', 'challenge']
        
        # Neutral/professional words
        professional_words = ['analyze', 'consider', 'evaluate', 'discuss', 'review', 'plan', 'strategy', 'objective', 'goal', 'process']
        
        text_lower = transcript.lower()
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        professional_count = sum(1 for word in professional_words if word in text_lower)
        
        total_emotional_words = positive_count + negative_count
        
        if total_emotional_words > 0:
            positive_ratio = positive_count / total_emotional_words
            
            if positive_ratio > 0.7:
                insights.append(ReflectionInsight(
                    category="Emotional Tone",
                    insight="Predominantly positive and enthusiastic conversation tone",
                    confidence=0.8,
                    evidence=[f"Positive indicators: {positive_count}, Negative indicators: {negative_count}"],
                    action_items=["Leverage this positive momentum", "Document what's working well"]
                ))
            elif positive_ratio < 0.3:
                insights.append(ReflectionInsight(
                    category="Emotional Tone",
                    insight="Conversation indicated concerns or challenges that need attention",
                    confidence=0.75,
                    evidence=[f"Negative indicators: {negative_count}, Positive indicators: {positive_count}"],
                    action_items=["Address identified concerns", "Develop action plan for challenges", "Follow up on emotional responses"]
                ))
            else:
                insights.append(ReflectionInsight(
                    category="Emotional Tone", 
                    insight="Balanced emotional tone with mixed sentiments",
                    confidence=0.6,
                    evidence=[f"Mixed emotional indicators: {positive_count} positive, {negative_count} negative"],
                    action_items=["Monitor sentiment trends", "Address any underlying concerns"]
                ))
        
        if professional_count > 5:
            insights.append(ReflectionInsight(
                category="Communication Style",
                insight="Professional and analytical discussion approach",
                confidence=0.7,
                evidence=[f"Found {professional_count} professional/analytical terms"],
                action_items=["Maintain professional tone in follow-ups"]
            ))
        
        return insights
    
    def _analyze_learning_opportunities(self, transcript: str, entities: List[Dict]) -> List[ReflectionInsight]:
        """Identify learning and development opportunities."""
        insights = []
        
        # Learning-related keywords
        learning_patterns = [
            r'\b(?:learn|learning|education|training|skill|knowledge|experience)\b',
            r'\b(?:new|innovative|creative|different|alternative)\b',
            r'\b(?:improve|better|enhance|develop|grow)\b',
            r'\b(?:mistake|error|lesson|feedback)\b'
        ]
        
        learning_mentions = 0
        for pattern in learning_patterns:
            learning_mentions += len(re.findall(pattern, transcript, re.IGNORECASE))
        
        if learning_mentions > 3:
            insights.append(ReflectionInsight(
                category="Learning Opportunities",
                insight="Conversation revealed multiple learning and development opportunities",
                confidence=0.75,
                evidence=[f"Found {learning_mentions} learning-related mentions"],
                action_items=[
                    "Identify specific learning goals",
                    "Research relevant training resources",
                    "Create learning action plan"
                ]
            ))
        
        # Knowledge gaps (questions without answers)
        questions = re.findall(r'[^.!?]*\?', transcript)
        if len(questions) > 2:
            insights.append(ReflectionInsight(
                category="Knowledge Gaps",
                insight=f"Identified {len(questions)} questions that may indicate knowledge gaps",
                confidence=0.7,
                evidence=questions[:2],  # Show first 2 questions as evidence
                action_items=[
                    "Research answers to outstanding questions",
                    "Identify subject matter experts",
                    "Schedule follow-up discussions"
                ]
            ))
        
        # Innovation and creativity indicators
        innovation_words = ['innovative', 'creative', 'new idea', 'brainstorm', 'think outside']
        innovation_count = sum(1 for word in innovation_words if word in transcript.lower())
        
        if innovation_count > 0:
            insights.append(ReflectionInsight(
                category="Innovation",
                insight="Discussion included innovative thinking and creative problem-solving",
                confidence=0.8,
                evidence=[f"Found {innovation_count} innovation-related mentions"],
                action_items=[
                    "Capture and develop creative ideas",
                    "Set up innovation follow-up session",
                    "Document novel approaches discussed"
                ]
            ))
        
        return insights
    
    def _analyze_decision_points(self, transcript: str, entities: List[Dict]) -> List[ReflectionInsight]:
        """Analyze decision points and consensus building."""
        insights = []
        
        # Decision-making language
        decision_patterns = [
            r'\b(?:decide|decided|decision|choose|chose|select|selected)\b',
            r'\b(?:agree|agreed|consensus|unanimous)\b', 
            r'\b(?:approve|approved|reject|rejected)\b',
            r'\b(?:vote|voted|poll)\b'
        ]
        
        decision_mentions = 0
        for pattern in decision_patterns:
            decision_mentions += len(re.findall(pattern, transcript, re.IGNORECASE))
        
        if decision_mentions > 3:
            insights.append(ReflectionInsight(
                category="Decision Making",
                insight="Active decision-making process with multiple decision points",
                confidence=0.8,
                evidence=[f"Found {decision_mentions} decision-related statements"],
                action_items=[
                    "Document all decisions made",
                    "Communicate decisions to stakeholders",
                    "Set implementation timelines"
                ]
            ))
        
        # Consensus and agreement analysis
        agreement_words = ['agree', 'consensus', 'unanimous', 'support', 'endorse']
        disagreement_words = ['disagree', 'oppose', 'concern', 'issue', 'problem', 'challenge']
        
        agreement_count = sum(1 for word in agreement_words if word in transcript.lower())
        disagreement_count = sum(1 for word in disagreement_words if word in transcript.lower())
        
        if agreement_count > disagreement_count and agreement_count > 2:
            insights.append(ReflectionInsight(
                category="Consensus Building",
                insight="Strong consensus and agreement achieved during discussion",
                confidence=0.8,
                evidence=[f"Agreement indicators: {agreement_count}, Disagreement indicators: {disagreement_count}"],
                action_items=["Leverage consensus for implementation", "Move forward with agreed plans"]
            ))
        elif disagreement_count > agreement_count:
            insights.append(ReflectionInsight(
                category="Consensus Building",
                insight="Areas of disagreement or concern identified that need resolution",
                confidence=0.75,
                evidence=[f"Disagreement indicators: {disagreement_count}, Agreement indicators: {agreement_count}"],
                action_items=[
                    "Address areas of disagreement",
                    "Schedule follow-up discussions",
                    "Seek additional input from stakeholders"
                ]
            ))
        
        return insights
    
    def _generate_summary(self, insights: List[ReflectionInsight], transcript: str, metadata: Dict) -> Dict[str, Any]:
        """Generate an overall summary of the analysis."""
        categories = {}
        total_confidence = 0
        
        for insight in insights:
            if insight.category not in categories:
                categories[insight.category] = []
            categories[insight.category].append(insight.insight)
            total_confidence += insight.confidence
        
        avg_confidence = total_confidence / len(insights) if insights else 0
        
        # Determine overall conversation type
        conversation_type = "General Discussion"
        if "Action Items" in categories and "Decisions" in categories:
            conversation_type = "Decision-Making Session"
        elif "Learning Opportunities" in categories:
            conversation_type = "Learning & Development"
        elif "Communication Style" in categories and len(categories) == 1:
            conversation_type = "Information Sharing"
        
        return {
            "conversation_type": conversation_type,
            "key_themes": list(categories.keys()),
            "overall_sentiment": self._determine_overall_sentiment(insights),
            "confidence_level": avg_confidence,
            "total_insights": len(insights),
            "word_count": len(transcript.split()),
            "analysis_completeness": min(1.0, len(insights) / 8),  # Assume 8 insights = complete analysis
            "primary_focus": max(categories.keys(), key=lambda k: len(categories[k])) if categories else "Unknown"
        }
    
    def _determine_overall_sentiment(self, insights: List[ReflectionInsight]) -> str:
        """Determine overall sentiment from insights."""
        emotional_insights = [i for i in insights if i.category == "Emotional Tone"]
        
        if not emotional_insights:
            return "Neutral"
        
        # Look at the emotional tone insights
        for insight in emotional_insights:
            if "positive" in insight.insight.lower():
                return "Positive"
            elif "concern" in insight.insight.lower() or "challenge" in insight.insight.lower():
                return "Concerned"
        
        return "Balanced"
    
    def _generate_recommendations(self, insights: List[ReflectionInsight], metadata: Dict) -> List[Dict[str, Any]]:
        """Generate actionable recommendations based on insights."""
        recommendations = []
        
        # Collect all action items
        all_action_items = []
        for insight in insights:
            all_action_items.extend(insight.action_items)
        
        # Group action items by category
        action_categories = {
            "immediate": [],
            "short_term": [],
            "long_term": []
        }
        
        immediate_keywords = ["follow up", "document", "communicate", "address"]
        long_term_keywords = ["develop", "create", "research", "learn"]
        
        for action in all_action_items:
            action_lower = action.lower()
            if any(keyword in action_lower for keyword in immediate_keywords):
                action_categories["immediate"].append(action)
            elif any(keyword in action_lower for keyword in long_term_keywords):
                action_categories["long_term"].append(action)
            else:
                action_categories["short_term"].append(action)
        
        # Create recommendations
        if action_categories["immediate"]:
            recommendations.append({
                "priority": "High",
                "timeframe": "Within 24 hours",
                "category": "Immediate Actions",
                "actions": action_categories["immediate"][:3],  # Top 3
                "rationale": "These actions will maintain momentum and address urgent items"
            })
        
        if action_categories["short_term"]:
            recommendations.append({
                "priority": "Medium",
                "timeframe": "Within 1 week",
                "category": "Short-term Planning",
                "actions": action_categories["short_term"][:3],
                "rationale": "These actions will build on the discussion outcomes"
            })
        
        if action_categories["long_term"]:
            recommendations.append({
                "priority": "Low",
                "timeframe": "Within 1 month",
                "category": "Strategic Development",
                "actions": action_categories["long_term"][:2],
                "rationale": "These actions will support long-term growth and improvement"
            })
        
        # Add specific recommendations based on insight patterns
        insight_categories = [i.category for i in insights]
        
        if "Learning Opportunities" in insight_categories:
            recommendations.append({
                "priority": "Medium",
                "timeframe": "Ongoing",
                "category": "Learning & Development",
                "actions": ["Schedule regular learning reviews", "Set up knowledge sharing sessions"],
                "rationale": "Continuous learning will enhance future discussions and outcomes"
            })
        
        if "Emotional Tone" in insight_categories:
            recommendations.append({
                "priority": "Medium", 
                "timeframe": "Ongoing",
                "category": "Relationship Building",
                "actions": ["Monitor team sentiment", "Celebrate successes", "Address concerns proactively"],
                "rationale": "Maintaining positive relationships supports better collaboration"
            })
        
        return recommendations