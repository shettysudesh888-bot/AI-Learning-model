import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from backend.models.entities import StudentProfile

ROOT_DIR = Path(__file__).resolve().parents[2]
MODEL_PATH = ROOT_DIR / "trained_models" / "random_forest_strategy.joblib"

STRATEGY_RESOURCES: dict[str, list[dict[str, str]]] = {
    "Video Tutorials": [
        {"type": "video", "title": "Short concept videos", "description": "Watch 8-12 minute topic explainers before practice."},
        {"type": "plan", "title": "Pause-and-solve routine", "description": "Pause after each example and solve one similar problem."},
    ],
    "Notes": [
        {"type": "notes", "title": "Structured notes", "description": "Use Cornell notes with summary prompts after each session."},
        {"type": "revision", "title": "Daily recap", "description": "Review highlighted formulas and definitions for 15 minutes."},
    ],
    "Practice Quizzes": [
        {"type": "quiz", "title": "Adaptive practice set", "description": "Attempt 10 mixed-difficulty questions after each topic."},
        {"type": "analytics", "title": "Mistake log", "description": "Track incorrect answers by concept and retry in 48 hours."},
    ],
    "Revision Plans": [
        {"type": "plan", "title": "Spaced revision", "description": "Revise on day 1, day 3, day 7, and day 14."},
        {"type": "checklist", "title": "Weekly consolidation", "description": "Summarize weak areas every Sunday."},
    ],
    "Mock Tests": [
        {"type": "test", "title": "Timed mock test", "description": "Take one timed paper and analyze speed plus accuracy."},
        {"type": "review", "title": "Post-test review", "description": "Spend equal time reviewing mistakes after the test."},
    ],
    "Pomodoro Technique": [
        {"type": "focus", "title": "25/5 focus cycle", "description": "Study for 25 minutes, rest 5 minutes, repeat three times."},
        {"type": "habit", "title": "Distraction list", "description": "Write distractions down and revisit them after the session."},
    ],
    "Group Study": [
        {"type": "collaboration", "title": "Peer explanation", "description": "Teach one concept to a peer and ask them to challenge gaps."},
        {"type": "discussion", "title": "Problem roundtable", "description": "Solve three problems together, rotating the explainer."},
    ],
    "Concept Maps": [
        {"type": "visual", "title": "Concept map", "description": "Draw topic relationships and add examples to each branch."},
        {"type": "recall", "title": "Blank map recall", "description": "Recreate the map from memory before checking notes."},
    ],
}


def profile_to_features(profile: StudentProfile) -> dict[str, Any]:
    return {
        "age": profile.age,
        "education_level": profile.education_level,
        "learning_style": profile.learning_style,
        "study_hours": profile.study_hours,
        "attention_span": profile.attention_span,
        "preferred_study_time": profile.preferred_study_time,
        "quiz_scores": profile.quiz_scores,
        "attendance": profile.attendance,
        "assignment_performance": profile.assignment_performance,
    }


def state_key(profile: StudentProfile) -> str:
    score = (profile.quiz_scores + profile.assignment_performance + profile.attendance) / 3
    level = "weak" if score < 55 else "developing" if score < 75 else "strong"
    attention = "short" if profile.attention_span < 30 else "steady" if profile.attention_span < 60 else "deep"
    hours = "low-hours" if profile.study_hours < 2 else "consistent"
    return f"{level}:{attention}:{hours}:{profile.learning_style.lower()}"


def _fallback_strategy(profile: StudentProfile) -> tuple[str, float]:
    weak_point = getattr(profile, "weak_point", "").lower()
    if "focus" in weak_point or "time" in weak_point:
        return "Pomodoro Technique", 0.66
    if "problem" in weak_point:
        return "Practice Quizzes", 0.66
    if "concept" in weak_point:
        return "Concept Maps", 0.64
    if "revision" in weak_point or "remember" in weak_point:
        return "Revision Plans", 0.64
    if profile.attention_span < 30:
        return "Pomodoro Technique", 0.62
    if profile.quiz_scores < 55:
        return "Practice Quizzes", 0.64
    if profile.assignment_performance < 60:
        return "Revision Plans", 0.61
    if profile.learning_style.lower() == "visual":
        return "Concept Maps", 0.6
    return "Mock Tests", 0.58


def predict_strategy(profile: StudentProfile) -> tuple[str, float, dict[str, float]]:
    if not MODEL_PATH.exists():
        strategy, confidence = _fallback_strategy(profile)
        return strategy, confidence, {strategy: confidence}

    bundle = joblib.load(MODEL_PATH)
    model = bundle["model"]
    features = pd.DataFrame([profile_to_features(profile)])
    probabilities = model.predict_proba(features)[0]
    classes = model.classes_
    score_map = {str(label): float(prob) for label, prob in zip(classes, probabilities)}
    strategy = str(classes[probabilities.argmax()])
    return strategy, float(probabilities.max()), score_map


def build_recommendation_payload(profile: StudentProfile, strategy: str, confidence: float, source: str) -> dict[str, Any]:
    weak_signals = []
    target_score = getattr(profile, "target_score", 80.0)
    weak_point = getattr(profile, "weak_point", "selected weak area")
    focus_topics = getattr(profile, "focus_topics", "").strip()
    plan_days = getattr(profile, "plan_days", 7)
    plan_mode = getattr(profile, "plan_mode", "improvement").replace("_", " ")
    score_gap = max(0, target_score - profile.quiz_scores)
    if profile.quiz_scores < 60:
        weak_signals.append("previous exam score")
    if score_gap >= 15:
        weak_signals.append(f"{score_gap:.0f}-point target gap")
    if weak_point:
        weak_signals.append(weak_point.lower())
    if profile.attendance < 75:
        weak_signals.append("attendance consistency")
    if profile.assignment_performance < 65:
        weak_signals.append("assignment performance")
    weakness_text = ", ".join(weak_signals) if weak_signals else "steady overall performance"
    rationale = (
        f"{strategy} fits the student's {profile.learning_style.lower()} preference, "
        f"current score of {profile.quiz_scores:.0f}%, target of {target_score:.0f}%, "
        f"and current signal around {weakness_text}. "
        f"The study plan uses {plan_days} days in {plan_mode} mode"
        f"{' and focuses on ' + focus_topics if focus_topics else ' as a full-subject improvement plan'}. "
        f"Recommendation source: {source}."
    )
    return {
        "strategy": strategy,
        "confidence": round(confidence, 3),
        "resources": STRATEGY_RESOURCES.get(strategy, STRATEGY_RESOURCES["Practice Quizzes"]),
        "rationale": rationale,
        "state_key": state_key(profile),
    }


def encode_resources(resources: list[dict[str, Any]]) -> str:
    return json.dumps(resources)


def decode_resources(resources: str) -> list[dict[str, Any]]:
    try:
        return json.loads(resources)
    except json.JSONDecodeError:
        return []
