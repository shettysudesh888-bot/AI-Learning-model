from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.models.entities import Feedback, Recommendation, User
from backend.rl_agent.q_learning import QLearningAgent, calculate_reward
from backend.schemas import FeedbackRequest, FeedbackResponse
from backend.utils.security import get_current_user

router = APIRouter()


@router.post("", response_model=FeedbackResponse)
def submit_feedback(
    payload: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    recommendation = (
        db.query(Recommendation)
        .filter(Recommendation.id == payload.recommendation_id, Recommendation.user_id == current_user.id)
        .first()
    )
    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    reward = calculate_reward(payload.rating, payload.helped, payload.score_before, payload.score_after)
    feedback = Feedback(
        user_id=current_user.id,
        recommendation_id=recommendation.id,
        rating=payload.rating,
        helped=1 if payload.helped else 0,
        score_before=payload.score_before,
        score_after=payload.score_after,
        comments=payload.comments,
        reward=reward,
    )
    db.add(feedback)
    QLearningAgent().update(recommendation.state_key, recommendation.strategy, reward)
    db.commit()
    db.refresh(feedback)
    return FeedbackResponse(id=feedback.id, reward=reward, message="Feedback saved and RL policy updated")
