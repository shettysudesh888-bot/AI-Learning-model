import re

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.models.entities import Recommendation, StudentProfile, StudyTask, User
from backend.recommendation_engine.engine import (
    build_recommendation_payload,
    decode_resources,
    encode_resources,
    predict_strategy,
    state_key,
)
from backend.recommendation_engine.groq_plan import generate_groq_plan
from backend.rl_agent.q_learning import QLearningAgent
from backend.schemas import RecommendationResponse
from backend.utils.security import get_current_user

router = APIRouter()


@router.get("/llm-status")
def llm_status():
    import os

    return {
        "groq_configured": bool(os.getenv("GROQ_API_KEY")),
        "groq_model": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
    }


def _subject_focus(subject: str) -> dict[str, str]:
    value = subject.lower()
    if "machine learning" in value or value.strip() in {"ml", "ai"}:
        return {
            "concept": "ML foundations and workflow",
            "practice": "data preprocessing and model practice",
            "test": "model evaluation mini test",
            "review": "bias, variance, and metric review",
        }
    if "react" in value:
        return {
            "concept": "React fundamentals",
            "practice": "component and state practice",
            "test": "small React app build",
            "review": "props, state, and component review",
        }
    if "math" in value:
        return {
            "concept": "formula and example review",
            "practice": "solve 12 mixed problems",
            "test": "timed problem set",
            "review": "calculation and step-error review",
        }
    if "physics" in value or "science" in value:
        return {
            "concept": "principle and diagram review",
            "practice": "solve numericals with units",
            "test": "concept plus numerical mini test",
            "review": "formula-use and assumption review",
        }
    if "program" in value or "coding" in value or "computer" in value:
        return {
            "concept": "read one concept and trace examples",
            "practice": "code 2 small exercises",
            "test": "debug one timed challenge",
            "review": "review errors and rewrite solution cleanly",
        }
    if "english" in value or "language" in value:
        return {
            "concept": "grammar or passage rule review",
            "practice": "write one answer and improve vocabulary",
            "test": "timed comprehension practice",
            "review": "review grammar and expression mistakes",
        }
    return {
        "concept": "core concept review",
        "practice": "focused practice session",
        "test": "short timed check",
        "review": "mistake review and correction",
    }


def _split_subjects(subjects: str) -> list[str]:
    normalized = re.sub(r"\s+(and|&)\s+", ",", subjects, flags=re.IGNORECASE)
    normalized = re.sub(r"[/|]+", ",", normalized)
    parsed = [subject.strip() for subject in normalized.replace(";", ",").split(",") if subject.strip()]
    cleaned = []
    for subject in parsed:
        lowered = subject.lower()
        if lowered in {"ml", "ai", "dl"}:
            cleaned.append(subject.upper())
        elif lowered == "react":
            cleaned.append("React")
        else:
            cleaned.append(subject)
    return cleaned or ["Selected subject"]


def _split_topics(topics: str) -> list[str]:
    normalized = re.sub(r"\s+(and|&)\s+", ",", topics or "", flags=re.IGNORECASE)
    normalized = re.sub(r"[/|]+", ",", normalized)
    return [topic.strip() for topic in normalized.replace(";", ",").split(",") if topic.strip()]


def build_study_tasks(profile: StudentProfile, strategy: str, recommendation_id: int, user_id: int) -> tuple[list[StudyTask], str]:
    subjects = _split_subjects(profile.subjects)
    groq_tasks = generate_groq_plan(profile, strategy) if len(subjects) == 1 else None
    if groq_tasks:
        return (
            [
                StudyTask(
                    user_id=user_id,
                    recommendation_id=recommendation_id,
                    day=task["day"],
                    time_slot=task.get("time_slot", ""),
                    title=task["title"],
                    description=task["description"],
                    duration_minutes=task["duration_minutes"],
                    completed=0,
                )
                for task in groq_tasks
            ],
            "Groq LLM",
        )

    weak = profile.weak_point.lower()
    gap = max(0, profile.target_score - profile.quiz_scores)
    minutes = max(20, min(90, int(profile.study_hours * 45)))

    if "time" in weak:
        emphasis = "Use a timer and stop after the planned time."
    elif "focus" in weak:
        emphasis = "Keep phone away and use one distraction note."
    elif "concept" in weak:
        emphasis = "Explain the idea in your own words before practice."
    elif "remember" in weak or "revision" in weak:
        emphasis = "Use active recall before checking notes."
    elif "fear" in weak:
        emphasis = "Start with easy questions, then attempt one exam-style task."
    else:
        emphasis = "Write every mistake in a mistake log."

    plan_days = max(3, min(30, int(getattr(profile, "plan_days", 7) or 7)))
    focus_topics = _split_topics(getattr(profile, "focus_topics", ""))
    plan_mode = (getattr(profile, "plan_mode", "improvement") or "improvement").lower()
    cycles = {
        "improvement": [
        ("Diagnostic Check", ["Identify weak spots in {focus_area}", "Solve a short baseline set", "Mark mistakes by type"]),
        ("Concept Repair", ["Review only the weak concept in {focus_area}", "Write a compact correction note", "Explain the idea in your own words"]),
        ("Guided Practice", ["Solve guided examples from {focus_area}", "Compare each solution step", "Add repeated errors to the mistake log"]),
        ("Timed Practice", ["Attempt a timed practice set on {focus_area}", "Track time spent per question", "Retry slow or incorrect questions"]),
        ("Mistake Correction", ["Rework previous mistakes in {focus_area}", "Write the reason for each error", "Create a quick recall checklist"]),
        ("Mini Mock", ["Take a focused mini test on {focus_area}", "Score accuracy and speed", "Choose two areas for tomorrow's repair"]),
        ("Revision Loop", ["Revise notes and mistake log for {focus_area}", "Use active recall before checking answers", "Set the next target for this subject"]),
        ],
        "focus": [
            ("Topic Diagnostic", ["List what is difficult in {focus_area}", "Solve 5 topic-specific questions", "Separate concept errors from careless errors"]),
            ("Topic Repair", ["Review the exact rule or method for {focus_area}", "Create a compact topic note", "Explain one example without looking at notes"]),
            ("Pattern Practice", ["Solve repeated patterns from {focus_area}", "Compare alternate solution methods", "Mark the fastest reliable method"]),
            ("Advanced Practice", ["Attempt harder questions from {focus_area}", "Track stuck points", "Redo one difficult question independently"]),
            ("Topic Test", ["Take a short test on {focus_area}", "Measure accuracy and time", "Revise only missed patterns"]),
        ],
        "revision": [
            ("Recall Check", ["Recall formulas or rules for {focus_area}", "Write key points from memory", "Check gaps against notes"]),
            ("Spaced Revision", ["Revise high-weight ideas in {focus_area}", "Use active recall before reading", "Create flash prompts"]),
            ("Past Mistake Review", ["Redo old mistakes from {focus_area}", "Write why each mistake happened", "Make a final correction list"]),
            ("Exam Drill", ["Attempt exam-style questions in {focus_area}", "Use strict time limits", "Review scoring opportunities"]),
            ("Final Recap", ["Create a one-page recap for {focus_area}", "Retry weak questions", "Plan the next revision date"]),
        ],
        "mock": [
            ("Mock Setup", ["Choose a focused mock set for {focus_area}", "Set time limits", "Define target accuracy"]),
            ("Timed Mock", ["Attempt a timed mock on {focus_area}", "Avoid checking notes during the test", "Record score and time"]),
            ("Mock Analysis", ["Review every wrong answer from {focus_area}", "Tag mistakes by concept, speed, or carelessness", "Pick 3 fixes"]),
            ("Retest", ["Redo incorrect mock questions", "Attempt similar new questions", "Compare accuracy improvement"]),
            ("Exam Strategy", ["Plan question order for {focus_area}", "Set skip and return rules", "Write the final test checklist"]),
        ],
    }
    selected_cycle = cycles.get(plan_mode, cycles["improvement"])

    topics = []
    for subject in subjects:
        focus = _subject_focus(subject)
        default_focus = f"{subject} weak areas"
        for index in range(plan_days):
            phase, task_templates = selected_cycle[index % len(selected_cycle)]
            topic = focus_topics[index % len(focus_topics)] if focus_topics else default_focus
            focus_area = f"{topic} in {subject}" if focus_topics else default_focus
            formatted_tasks = [
                task.format(
                    subject=subject,
                    focus_area=focus_area,
                    concept=focus["concept"],
                    practice=focus["practice"],
                    test=focus["test"],
                    review=focus["review"],
                )
                for task in task_templates
            ]
            topics.append((f"Day {index + 1}", f"{subject} - {phase}", formatted_tasks))

    plan = []
    for day, topic, tasks in topics:
        for index, task in enumerate(tasks, start=1):
            description = emphasis if index < len(tasks) else f"Project: {task}" if "build" in task.lower() or "project" in task.lower() else "Mark status after completing this task."
            plan.append((day, topic, task, description, max(25, minutes // len(tasks))))
    return (
        [
            StudyTask(
                user_id=user_id,
                recommendation_id=recommendation_id,
                day=day,
                time_slot=time_slot,
                title=title,
                description=description,
                duration_minutes=duration,
                completed=0,
            )
            for day, time_slot, title, description, duration in plan
        ],
        "Local fallback",
    )


def _to_response(row: Recommendation) -> RecommendationResponse:
    tasks = [
        {
            "id": task.id,
            "day": task.day,
            "time_slot": task.time_slot,
            "title": task.title,
            "description": task.description,
            "duration_minutes": task.duration_minutes,
            "completed": task.completed,
        }
        for task in row.user.study_tasks
        if task.recommendation_id == row.id
    ]
    return RecommendationResponse(
        id=row.id,
        strategy=row.strategy,
        confidence=row.confidence,
        resources=decode_resources(row.resources),
        study_plan=tasks,
        plan_source="Groq LLM" if "Study plan source: Groq LLM" in row.rationale else "Local fallback",
        rationale=row.rationale,
        state_key=row.state_key,
        created_at=row.created_at,
    )


@router.post("", response_model=RecommendationResponse)
def create_recommendation(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).one()
    ml_strategy, ml_confidence, _scores = predict_strategy(profile)
    agent = QLearningAgent()
    chosen_strategy, source = agent.choose_action(state_key(profile), ml_strategy)
    payload = build_recommendation_payload(profile, chosen_strategy, ml_confidence, source)
    row = Recommendation(
        user_id=current_user.id,
        strategy=payload["strategy"],
        confidence=payload["confidence"],
        resources=encode_resources(payload["resources"]),
        rationale=payload["rationale"],
        state_key=payload["state_key"],
    )
    db.add(row)
    db.flush()
    db.query(StudyTask).filter(StudyTask.user_id == current_user.id).delete()
    study_tasks, plan_source = build_study_tasks(profile, payload["strategy"], row.id, current_user.id)
    row.rationale = f"{row.rationale} Study plan source: {plan_source}."
    db.add_all(study_tasks)
    db.commit()
    db.refresh(row)
    return _to_response(row)


@router.get("/history", response_model=list[RecommendationResponse])
def history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(Recommendation)
        .filter(Recommendation.user_id == current_user.id)
        .order_by(Recommendation.created_at.desc())
        .limit(20)
        .all()
    )
    return [_to_response(row) for row in rows]
