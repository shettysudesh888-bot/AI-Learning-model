from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.models.entities import StudentProfile, User
from backend.schemas import ProfileBase, ProfileResponse
from backend.utils.security import get_current_user

router = APIRouter()


@router.get("/me", response_model=ProfileResponse)
def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).one()


@router.put("/me", response_model=ProfileResponse)
def update_profile(
    payload: ProfileBase,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).one()
    for key, value in payload.model_dump().items():
        setattr(profile, key, value)
    profile.setup_completed = 1
    db.commit()
    db.refresh(profile)
    return profile
