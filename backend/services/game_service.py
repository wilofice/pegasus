"""Game service for question generation and answer validation using Ollama LLM."""
import logging
import json
import re
from typing import Dict, Any, List, Optional

from services.ollama_service import OllamaService
from schemas.game import Question, QuestionType, UserAnswer, ValidationResponse

logger = logging.getLogger(__name__)


class GameService:
    """Service for handling game logic with LLM integration."""
    
    def __init__(self):
        self.ollama_service = OllamaService()
    
    async def generate_question(self, topic: str, difficulty: str = "medium", 
                              previous_questions: Optional[List[Question]] = None) -> Dict[str, Any]:
        """Generate a question on the given topic.
        
        Args:
            topic: The topic for the question
            difficulty: Difficulty level (easy, medium, hard)
            previous_questions: List of previously asked questions to avoid repetition
            
        Returns:
            Dictionary with question generation results
        """
        # Build context from previous questions to avoid repetition
        previous_context = ""
        if previous_questions:
            topics_covered = [q.text[:50] + "..." for q in previous_questions[-5:]]  # Last 5 questions
            previous_context = f"\n\nPrevious questions asked (avoid similar topics):\n" + "\n".join(topics_covered)
        
        system_prompt = f"""You are an expert educator creating educational quiz questions. Generate a single question about the given topic with the specified difficulty level.

IMPORTANT: Respond ONLY with valid JSON in exactly this format:
{{
    "id": "q_unique_id",
    "text": "The question text here?",
    "type": "SINGLE_CHOICE|MULTIPLE_CHOICE|FREE_TEXT",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "hint": "Optional hint text",
    "difficulty": "{difficulty}"
}}

Rules:
1. For SINGLE_CHOICE: Exactly 4 options, only one correct
2. For MULTIPLE_CHOICE: 4-6 options, 2-3 correct answers
3. For FREE_TEXT: No options array needed
4. Make questions engaging and educational
5. Difficulty levels: easy (basic facts), medium (understanding), hard (analysis/application)
6. Generate a unique ID for each question
7. DO NOT include any text before or after the JSON"""

        user_prompt = f"""Topic: {topic}
Difficulty: {difficulty}{previous_context}

Generate an educational question about this topic."""
        
        logger.info(f"Generating question on topic: {topic} (difficulty: {difficulty})")
        result = await self.ollama_service.generate_completion(user_prompt, system_prompt)
        
        if not result["success"]:
            return {
                "success": False,
                "error": result.get("error", "Failed to generate question")
            }
        
        try:
            # Clean the response to extract JSON
            response_text = result["response"].strip()
            
            # Find JSON content (remove any surrounding text)
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group()
            else:
                json_text = response_text
            
            # Parse JSON
            question_data = json.loads(json_text)
            
            # Validate required fields
            required_fields = ["id", "text", "type"]
            for field in required_fields:
                if field not in question_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate question type
            question_type = question_data["type"]
            if question_type not in ["SINGLE_CHOICE", "MULTIPLE_CHOICE", "FREE_TEXT"]:
                raise ValueError(f"Invalid question type: {question_type}")
            
            # Validate options for choice questions
            if question_type in ["SINGLE_CHOICE", "MULTIPLE_CHOICE"]:
                if "options" not in question_data or not question_data["options"]:
                    raise ValueError(f"Options required for {question_type} questions")
                
                if question_type == "SINGLE_CHOICE" and len(question_data["options"]) != 4:
                    logger.warning(f"Single choice question should have 4 options, got {len(question_data['options'])}")
            
            # Create Question object
            question = Question(
                id=question_data["id"],
                text=question_data["text"],
                type=QuestionType(question_type),
                options=question_data.get("options"),
                hint=question_data.get("hint"),
                difficulty=question_data.get("difficulty", difficulty)
            )
            
            return {
                "success": True,
                "question": question,
                "model": result.get("model")
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse question JSON: {e}")
            logger.error(f"Raw response: {result['response']}")
            return {
                "success": False,
                "error": f"Invalid JSON response from LLM: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error processing generated question: {e}")
            return {
                "success": False,
                "error": f"Failed to process question: {str(e)}"
            }
    
    async def validate_answer(self, question: Question, user_answer: UserAnswer) -> Dict[str, Any]:
        """Validate a user's answer to a question.
        
        Args:
            question: The question that was answered
            user_answer: The user's answer
            
        Returns:
            Dictionary with validation results
        """
        # Prepare user answer text
        if question.type == QuestionType.FREE_TEXT:
            answer_text = user_answer.custom_text or ""
        else:
            answer_text = ", ".join(user_answer.selected_options or [])
        
        system_prompt = """You are an expert educator evaluating student answers. Analyze the student's answer and provide feedback.

IMPORTANT: Respond ONLY with valid JSON in exactly this format:
{
    "is_correct": true/false,
    "explanation": "Detailed explanation of why the answer is correct or incorrect, and what the correct answer should be",
    "correct_answer": "The correct answer (for reference)",
    "score_points": 0-10
}

Rules:
1. For multiple choice: Check if selected options are correct
2. For free text: Be flexible with wording but check for accuracy
3. Give partial credit when appropriate (score_points 1-9 for partially correct)
4. Always provide educational explanation
5. Score: 10 points for fully correct, 5-9 for partially correct, 0 for incorrect
6. DO NOT include any text before or after the JSON"""

        user_prompt = f"""Question: {question.text}
Question Type: {question.type.value}
Question Options: {question.options if question.options else "N/A"}

Student Answer: {answer_text}

Evaluate this answer and provide feedback."""
        
        logger.info(f"Validating answer for question: {question.id}")
        result = await self.ollama_service.generate_completion(user_prompt, system_prompt)
        
        if not result["success"]:
            return {
                "success": False,
                "error": result.get("error", "Failed to validate answer")
            }
        
        try:
            # Clean the response to extract JSON
            response_text = result["response"].strip()
            
            # Find JSON content
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group()
            else:
                json_text = response_text
            
            # Parse JSON
            validation_data = json.loads(json_text)
            
            # Validate required fields
            required_fields = ["is_correct", "explanation", "score_points"]
            for field in required_fields:
                if field not in validation_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Ensure score is within valid range
            score = validation_data["score_points"]
            if not isinstance(score, (int, float)) or score < 0 or score > 10:
                logger.warning(f"Invalid score {score}, setting to 0 or 10")
                score = 10 if validation_data["is_correct"] else 0
            
            # Create ValidationResponse object
            validation = ValidationResponse(
                is_correct=bool(validation_data["is_correct"]),
                explanation=validation_data["explanation"],
                correct_answer=validation_data.get("correct_answer"),
                score_points=int(score)
            )
            
            return {
                "success": True,
                "validation": validation,
                "model": result.get("model")
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse validation JSON: {e}")
            logger.error(f"Raw response: {result['response']}")
            return {
                "success": False,
                "error": f"Invalid JSON response from LLM: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error processing answer validation: {e}")
            return {
                "success": False,
                "error": f"Failed to process validation: {str(e)}"
            }
    
    async def generate_questions_batch(self, topic: str, count: int, difficulty: str = "medium") -> Dict[str, Any]:
        """Generate multiple questions for a game session.
        
        Args:
            topic: The topic for questions
            count: Number of questions to generate
            difficulty: Difficulty level
            
        Returns:
            Dictionary with batch generation results
        """
        questions = []
        errors = []
        
        for i in range(count):
            try:
                result = await self.generate_question(topic, difficulty, questions)
                if result["success"]:
                    questions.append(result["question"])
                    logger.info(f"Generated question {i+1}/{count}")
                else:
                    error_msg = f"Question {i+1}: {result['error']}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            except Exception as e:
                error_msg = f"Question {i+1}: Unexpected error - {e}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        return {
            "success": len(questions) > 0,
            "questions": questions,
            "generated_count": len(questions),
            "requested_count": count,
            "errors": errors
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check game service health.
        
        Returns:
            Dictionary with health status
        """
        ollama_health = await self.ollama_service.health_check()
        
        return {
            "healthy": ollama_health["healthy"],
            "service": "GameService",
            "ollama_status": ollama_health
        }