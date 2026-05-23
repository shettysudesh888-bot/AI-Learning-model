import json
import os
import urllib.error
import urllib.request

from backend.models.entities import StudentProfile

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")


def generate_groq_plan(profile: StudentProfile, strategy: str) -> list[dict] | None:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None

    prompt = {
        "subject": profile.subjects,
        "previous_score": profile.quiz_scores,
        "target_score": profile.target_score,
        "weak_point": profile.weak_point,
        "focus_topics": getattr(profile, "focus_topics", ""),
        "plan_days": getattr(profile, "plan_days", 7),
        "plan_mode": getattr(profile, "plan_mode", "improvement"),
        "learning_style": profile.learning_style,
        "study_hours_per_day": profile.study_hours,
        "preferred_time": profile.preferred_study_time,
        "strategy": strategy,
    }
    body = {
        "model": GROQ_MODEL,
        "temperature": 0.25,
        "max_tokens": 1200,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You create topic-based 7-day learning roadmaps. Return ONLY valid JSON, no markdown. "
                    "The JSON must cover the requested number of plan_days, with 3 or 4 task rows per day. "
                    "Each day must contain 3 or 4 task rows. Each object must have keys: "
                    "day, time_slot, title, description, duration_minutes. Use time_slot to store the day topic, "
                    "for example 'React - Timed Practice' or 'ML - Mistake Correction'. "
                    "Do not create a beginner introduction unless the weak point or focus topic requires it. "
                    "Follow plan_mode: improvement, focus, revision, or mock. "
                    "If focus_topics are provided, center the plan on those topics. Otherwise, make a full-subject improvement plan. "
                    "If the subject field contains multiple comma-separated subjects, rotate them across the week "
                    "and include the subject name in each day topic. "
                    "Each title must be a clear task row. Description may contain a mini project only for the final task of a day. "
                    "Make it subject-specific, sequential, and beginner-friendly."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(prompt),
            },
        ],
    }
    request = urllib.request.Request(
        GROQ_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None

    content = payload.get("choices", [{}])[0].get("message", {}).get("content", "")
    try:
        tasks = json.loads(content)
    except json.JSONDecodeError:
        start = content.find("[")
        end = content.rfind("]")
        if start == -1 or end == -1:
            return None
        try:
            tasks = json.loads(content[start : end + 1])
        except json.JSONDecodeError:
            return None

    if not isinstance(tasks, list) or len(tasks) < 14:
        return None

    cleaned = []
    for task in tasks:
        if not isinstance(task, dict):
            return None
        cleaned.append(
            {
                "day": str(task.get("day", ""))[:20],
                "time_slot": str(task.get("time_slot", ""))[:40],
                "title": str(task.get("title", ""))[:160],
                "description": str(task.get("description", "")),
                "duration_minutes": int(task.get("duration_minutes", max(20, int(profile.study_hours * 45)))),
            }
        )
    return cleaned
