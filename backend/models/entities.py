from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="student")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    profile: Mapped["StudentProfile"] = relationship(back_populates="user", uselist=False)
    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="user")
    feedback_items: Mapped[list["Feedback"]] = relationship(back_populates="user")
    study_tasks: Mapped[list["StudyTask"]] = relationship(back_populates="user")


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), default="")
    age: Mapped[int] = mapped_column(Integer, default=18)
    education_level: Mapped[str] = mapped_column(String(80), default="Undergraduate")
    subjects: Mapped[str] = mapped_column(Text, default="Mathematics, Science")
    learning_style: Mapped[str] = mapped_column(String(40), default="Visual")
    study_hours: Mapped[float] = mapped_column(Float, default=2.0)
    attention_span: Mapped[int] = mapped_column(Integer, default=35)
    preferred_study_time: Mapped[str] = mapped_column(String(40), default="Evening")
    quiz_scores: Mapped[float] = mapped_column(Float, default=70.0)
    target_score: Mapped[float] = mapped_column(Float, default=80.0)
    weak_point: Mapped[str] = mapped_column(String(80), default="Problem solving")
    focus_topics: Mapped[str] = mapped_column(Text, default="")
    plan_days: Mapped[int] = mapped_column(Integer, default=7)
    plan_mode: Mapped[str] = mapped_column(String(40), default="improvement")
    attendance: Mapped[float] = mapped_column(Float, default=85.0)
    assignment_performance: Mapped[float] = mapped_column(Float, default=72.0)
    setup_completed: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="profile")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    strategy: Mapped[str] = mapped_column(String(80), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    resources: Mapped[str] = mapped_column(Text, default="[]")
    rationale: Mapped[str] = mapped_column(Text, default="")
    state_key: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="recommendations")
    feedback: Mapped["Feedback"] = relationship(back_populates="recommendation", uselist=False)


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    recommendation_id: Mapped[int] = mapped_column(ForeignKey("recommendations.id"), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    helped: Mapped[int] = mapped_column(Integer, default=1)
    score_before: Mapped[float] = mapped_column(Float, default=0)
    score_after: Mapped[float] = mapped_column(Float, default=0)
    comments: Mapped[str] = mapped_column(Text, default="")
    reward: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="feedback_items")
    recommendation: Mapped[Recommendation] = relationship(back_populates="feedback")


class StudyTask(Base):
    __tablename__ = "study_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    recommendation_id: Mapped[int] = mapped_column(ForeignKey("recommendations.id"), nullable=False)
    day: Mapped[str] = mapped_column(String(20), nullable=False)
    time_slot: Mapped[str] = mapped_column(String(40), default="")
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    completed: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="study_tasks")
