"""Core game models and session management."""
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from uuid import uuid4

from schemas.game import Question, UserAnswer, ValidationResponse, QuestionType


@dataclass
class GameSession:
    """Game session data class."""
    session_id: str
    topic: str
    total_questions: int
    difficulty: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    
    # Game state
    current_question_index: int = 0
    questions: List[Question] = field(default_factory=list)
    answers: List[UserAnswer] = field(default_factory=list)
    validations: List[ValidationResponse] = field(default_factory=list)
    
    # Scoring
    total_score: int = 0
    max_possible_score: int = 0
    
    @property
    def is_completed(self) -> bool:
        """Check if the game session is completed."""
        return self.current_question_index >= len(self.questions)
    
    @property
    def current_question(self) -> Optional[Question]:
        """Get the current question."""
        if self.current_question_index < len(self.questions):
            return self.questions[self.current_question_index]
        return None
    
    @property
    def progress(self) -> Dict[str, int]:
        """Get game progress information."""
        return {
            "current": self.current_question_index,
            "total": len(self.questions),
            "remaining": len(self.questions) - self.current_question_index
        }
    
    @property
    def correct_answers(self) -> int:
        """Count correct answers."""
        return sum(1 for v in self.validations if v.is_correct)
    
    @property
    def incorrect_answers(self) -> int:
        """Count incorrect answers."""
        return sum(1 for v in self.validations if not v.is_correct)
    
    @property
    def percentage_score(self) -> float:
        """Calculate percentage score."""
        if self.max_possible_score == 0:
            return 0.0
        return (self.total_score / self.max_possible_score) * 100
    
    def add_answer(self, answer: UserAnswer, validation: ValidationResponse) -> None:
        """Add an answer and its validation to the session."""
        self.answers.append(answer)
        self.validations.append(validation)
        self.total_score += validation.score_points
        self.current_question_index += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary."""
        return {
            "session_id": self.session_id,
            "topic": self.topic,
            "total_questions": self.total_questions,
            "difficulty": self.difficulty,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "current_question_index": self.current_question_index,
            "total_score": self.total_score,
            "max_possible_score": self.max_possible_score,
            "is_completed": self.is_completed,
            "progress": self.progress,
            "correct_answers": self.correct_answers,
            "incorrect_answers": self.incorrect_answers,
            "percentage_score": self.percentage_score
        }


class GameSessionManager:
    """In-memory game session manager."""
    
    def __init__(self):
        self.sessions: Dict[str, GameSession] = {}
    
    def create_session(self, topic: str, total_questions: int, difficulty: str = "medium") -> GameSession:
        """Create a new game session."""
        session_id = str(uuid4())
        session = GameSession(
            session_id=session_id,
            topic=topic,
            total_questions=total_questions,
            difficulty=difficulty,
            started_at=datetime.utcnow()
        )
        self.sessions[session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[GameSession]:
        """Get a game session by ID."""
        return self.sessions.get(session_id)
    
    def update_session(self, session: GameSession) -> None:
        """Update a game session."""
        self.sessions[session.session_id] = session
    
    def delete_session(self, session_id: str) -> None:
        """Delete a game session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
    
    def cleanup_old_sessions(self, max_age_hours: int = 24) -> None:
        """Clean up old sessions."""
        cutoff_time = datetime.utcnow().timestamp() - (max_age_hours * 3600)
        to_delete = []
        
        for session_id, session in self.sessions.items():
            if session.started_at.timestamp() < cutoff_time:
                to_delete.append(session_id)
        
        for session_id in to_delete:
            del self.sessions[session_id]


# Global session manager instance
game_session_manager = GameSessionManager()