from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.models.entities import StudentProfile, User
from backend.schemas import LoginRequest, RegisterRequest, TokenResponse
from backend.utils.security import create_access_token, get_current_user, hash_password, verify_password

router = APIRouter()


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    role = "admin" if payload.role.lower() == "admin" else "student"
    user = User(email=payload.email.lower(), password_hash=hash_password(payload.password), role=role)
    db.add(user)
    db.flush()
    if role == "student":
        db.add(StudentProfile(user_id=user.id, name=payload.name))
    db.commit()
    return TokenResponse(access_token=create_access_token(str(user.id)), role=user.role or "student")


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return TokenResponse(access_token=create_access_token(str(user.id)), role=user.role or "student")


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email, "role": current_user.role}
