"""Pydantic schemas for game API requests and responses."""
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field


class QuestionType(str, Enum):
    """Question type enumeration."""
    SINGLE_CHOICE = "SINGLE_CHOICE"
    MULTIPLE_CHOICE = "MULTIPLE_CHOICE"
    FREE_TEXT = "FREE_TEXT"


class Question(BaseModel):
    """Question model."""
    id: str = Field(..., description="Unique question identifier")
    text: str = Field(..., description="Question text")
    type: QuestionType = Field(..., description="Type of question")
    options: Optional[List[str]] = Field(None, description="Answer options for choice questions")
    hint: Optional[str] = Field(None, description="Optional hint for the question")
    difficulty: Optional[str] = Field("medium", description="Question difficulty level")


class UserAnswer(BaseModel):
    """User answer model."""
    question_id: str = Field(..., description="ID of the question being answered")
    selected_options: Optional[List[str]] = Field(None, description="Selected options for choice questions")
    custom_text: Optional[str] = Field(None, description="Custom text answer for free text questions") 


class ValidationResponse(BaseModel):
    """Answer validation response model."""
    is_correct: bool = Field(..., description="Whether the answer is correct")
    explanation: str = Field(..., description="Explanation of the correct answer")
    correct_answer: Optional[str] = Field(None, description="The correct answer if user was wrong")
    score_points: int = Field(0, description="Points awarded for this answer")


class GameStartRequest(BaseModel):
    """Game start request model."""
    topic: str = Field(..., description="Topic for the game questions", min_length=1, max_length=200)
    length: int = Field(10, description="Number of questions desired", ge=1, le=50)
    difficulty: Optional[str] = Field("medium", description="Game difficulty level")


class GameStartResponse(BaseModel):
    """Game start response model."""
    session_id: str = Field(..., description="Unique session identifier")
    first_question: Question = Field(..., description="First question in the game")
    total_questions: int = Field(..., description="Total number of questions in this game")


class GameAnswerRequest(BaseModel):
    """Game answer request model."""
    answer: UserAnswer = Field(..., description="User's answer to the current question")


class GameAnswerResponse(BaseModel):
    """Game answer response model."""
    validation: ValidationResponse = Field(..., description="Validation result for the answer")
    next_question: Optional[Question] = Field(None, description="Next question, if game continues")
    game_completed: bool = Field(False, description="Whether the game is completed")
    current_score: int = Field(0, description="Current total score")
    progress: Dict[str, int] = Field(default_factory=dict, description="Game progress info")


class GameSummaryResponse(BaseModel):
    """Game summary response model."""
    session_id: str = Field(..., description="Session identifier")
    topic: str = Field(..., description="Game topic")
    total_questions: int = Field(..., description="Total number of questions")
    answered_questions: int = Field(..., description="Number of questions answered")
    total_score: int = Field(..., description="Total score achieved")
    max_possible_score: int = Field(..., description="Maximum possible score")
    percentage_score: float = Field(..., description="Score as percentage")
    correct_answers: int = Field(..., description="Number of correct answers")
    incorrect_answers: int = Field(..., description="Number of incorrect answers")
    started_at: datetime = Field(..., description="Game start time")
    completed_at: Optional[datetime] = Field(None, description="Game completion time")
    duration_minutes: Optional[float] = Field(None, description="Game duration in minutes")