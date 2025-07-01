"""Game API router for the learning game feature."""
import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from schemas.game import (
    GameStartRequest, GameStartResponse, GameAnswerRequest, GameAnswerResponse,
    GameSummaryResponse, Question
)
from services.game_service import GameService
from core.game_models import game_session_manager, GameSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/game", tags=["game"])

# Dependency to get game service
async def get_game_service() -> GameService:
    """Get game service instance."""
    return GameService()


@router.post("/start", response_model=GameStartResponse)
async def start_game(
    request: GameStartRequest,
    game_service: GameService = Depends(get_game_service)
) -> GameStartResponse:
    """Start a new learning game session.
    
    Args:
        request: Game start request with topic and settings
        game_service: Game service dependency
        
    Returns:
        Game start response with session ID and first question
        
    Raises:
        HTTPException: If game cannot be started
    """
    try:
        logger.info(f"Starting new game: topic='{request.topic}', length={request.length}")
        
        # Create new game session
        session = game_session_manager.create_session(
            topic=request.topic,
            total_questions=request.length,
            difficulty=request.difficulty or "medium"
        )
        
        # Generate the first question
        result = await game_service.generate_question(
            topic=request.topic,
            difficulty=session.difficulty
        )
        
        if not result["success"]:
            # Clean up failed session
            game_session_manager.delete_session(session.session_id)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate first question: {result['error']}"
            )
        
        first_question = result["question"]
        
        # Add the question to session (but don't increment index yet)
        session.questions.append(first_question)
        session.max_possible_score += 10  # Each question worth 10 points max
        game_session_manager.update_session(session)
        
        logger.info(f"Game started successfully: session_id={session.session_id}")
        
        return GameStartResponse(
            session_id=session.session_id,
            first_question=first_question,
            total_questions=session.total_questions
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting game: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start game: {str(e)}"
        )


@router.post("/answer/{session_id}", response_model=GameAnswerResponse)
async def submit_answer(
    session_id: str,
    request: GameAnswerRequest,
    game_service: GameService = Depends(get_game_service)
) -> GameAnswerResponse:
    """Submit an answer for the current question.
    
    Args:
        session_id: Game session identifier
        request: User's answer to the current question
        game_service: Game service dependency
        
    Returns:
        Answer validation result and next question (if game continues)
        
    Raises:
        HTTPException: If session not found or answer cannot be processed
    """
    try:
        # Get game session
        session = game_session_manager.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail="Game session not found"
            )
        
        # Check if game is already completed
        if session.is_completed:
            raise HTTPException(
                status_code=400,
                detail="Game is already completed"
            )
        
        # Get current question
        current_question = session.current_question
        if not current_question:
            raise HTTPException(
                status_code=400,
                detail="No current question available"
            )
        
        # Validate the answer
        logger.info(f"Validating answer for session {session_id}, question {current_question.id}")
        validation_result = await game_service.validate_answer(current_question, request.answer)
        
        if not validation_result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to validate answer: {validation_result['error']}"
            )
        
        validation = validation_result["validation"]
        
        # Add answer and validation to session
        session.add_answer(request.answer, validation)
        
        # Check if we need to generate next question
        next_question = None
        game_completed = session.is_completed
        
        if not game_completed and session.current_question_index < session.total_questions:
            # Generate next question
            next_result = await game_service.generate_question(
                topic=session.topic,
                difficulty=session.difficulty,
                previous_questions=session.questions
            )
            
            if next_result["success"]:
                next_question = next_result["question"]
                session.questions.append(next_question)
                session.max_possible_score += 10  # Each question worth 10 points max
            else:
                logger.warning(f"Failed to generate next question: {next_result['error']}")
                # Mark game as completed if we can't generate more questions
                game_completed = True
        else:
            game_completed = True
        
        # Mark game as completed if this was the last question
        if game_completed and not session.completed_at:
            session.completed_at = datetime.utcnow()
        
        # Update session
        game_session_manager.update_session(session)
        
        logger.info(f"Answer processed for session {session_id}: correct={validation.is_correct}, score={validation.score_points}")
        
        return GameAnswerResponse(
            validation=validation,
            next_question=next_question,
            game_completed=game_completed,
            current_score=session.total_score,
            progress=session.progress
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing answer for session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process answer: {str(e)}"
        )


@router.get("/summary/{session_id}", response_model=GameSummaryResponse)
async def get_game_summary(session_id: str) -> GameSummaryResponse:
    """Get game summary and final results.
    
    Args:
        session_id: Game session identifier
        
    Returns:
        Complete game summary with scores and statistics
        
    Raises:
        HTTPException: If session not found
    """
    try:
        # Get game session
        session = game_session_manager.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail="Game session not found"
            )
        
        # Calculate duration
        duration_minutes = None
        if session.completed_at:
            duration_seconds = (session.completed_at - session.started_at).total_seconds()
            duration_minutes = duration_seconds / 60
        
        logger.info(f"Generated summary for session {session_id}")
        
        return GameSummaryResponse(
            session_id=session.session_id,
            topic=session.topic,
            total_questions=session.total_questions,
            answered_questions=len(session.answers),
            total_score=session.total_score,
            max_possible_score=session.max_possible_score,
            percentage_score=session.percentage_score,
            correct_answers=session.correct_answers,
            incorrect_answers=session.incorrect_answers,
            started_at=session.started_at,
            completed_at=session.completed_at,
            duration_minutes=duration_minutes
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting summary for session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get game summary: {str(e)}"
        )


@router.get("/session/{session_id}", response_model=Dict[str, Any])
async def get_game_session(session_id: str) -> Dict[str, Any]:
    """Get current game session details (for debugging/monitoring).
    
    Args:
        session_id: Game session identifier
        
    Returns:
        Current session state
        
    Raises:
        HTTPException: If session not found
    """
    try:
        session = game_session_manager.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail="Game session not found"
            )
        
        return session.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get session: {str(e)}"
        )


@router.delete("/session/{session_id}")
async def delete_game_session(session_id: str) -> Dict[str, str]:
    """Delete a game session.
    
    Args:
        session_id: Game session identifier
        
    Returns:
        Deletion confirmation
        
    Raises:
        HTTPException: If session not found
    """
    try:
        session = game_session_manager.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail="Game session not found"
            )
        
        game_session_manager.delete_session(session_id)
        logger.info(f"Deleted session {session_id}")
        
        return {"message": f"Session {session_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete session: {str(e)}"
        )


@router.get("/health")
async def health_check(game_service: GameService = Depends(get_game_service)) -> Dict[str, Any]:
    """Health check endpoint for game service.
    
    Returns:
        Health status of game service and dependencies
    """
    try:
        health_status = await game_service.health_check()
        active_sessions = len(game_session_manager.sessions)
        
        return {
            **health_status,
            "active_sessions": active_sessions,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "healthy": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }