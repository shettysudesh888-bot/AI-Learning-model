from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = Field(min_length=1)
    role: str = "student"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str = "student"


class ProfileBase(BaseModel):
    name: str
    age: int = Field(ge=10, le=80)
    education_level: str
    subjects: str
    learning_style: str
    study_hours: float = Field(ge=0, le=16)
    attention_span: int = Field(ge=5, le=180)
    preferred_study_time: str
    quiz_scores: float = Field(ge=0, le=100)
    target_score: float = Field(ge=0, le=100)
    weak_point: str
    focus_topics: str = ""
    plan_days: int = Field(default=7, ge=3, le=30)
    plan_mode: str = "improvement"
    attendance: float = Field(ge=0, le=100)
    assignment_performance: float = Field(ge=0, le=100)


class ProfileResponse(ProfileBase):
    id: int
    setup_completed: int
    updated_at: datetime

    model_config = {"from_attributes": True}


class RecommendationResponse(BaseModel):
    id: int
    strategy: str
    confidence: float
    resources: list[dict[str, Any]]
    study_plan: list[dict[str, Any]] = []
    plan_source: str = "Unknown"
    rationale: str
    state_key: str
    created_at: datetime


class FeedbackRequest(BaseModel):
    recommendation_id: int
    rating: int = Field(ge=1, le=5)
    helped: bool
    score_before: float = Field(ge=0, le=100)
    score_after: float = Field(ge=0, le=100)
    comments: str = ""


class FeedbackResponse(BaseModel):
    id: int
    reward: float
    message: str


class StudyTaskResponse(BaseModel):
    id: int
    recommendation_id: int
    day: str
    time_slot: str = ""
    title: str
    description: str
    duration_minutes: int
    completed: int

    model_config = {"from_attributes": True}


class StudyTaskUpdate(BaseModel):
    completed: bool
