import json
import os
import urllib.error
import urllib.request

from backend.models.entities import StudentProfile

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
LAST_GROQ_ATTEMPT = {
    "attempted": False,
    "success": False,
    "reason": "No Groq request has been attempted yet.",
    "model": GROQ_MODEL,
}


def groq_status() -> dict:
    return {
        "groq_configured": bool(os.getenv("GROQ_API_KEY")),
        "groq_model": os.getenv("GROQ_MODEL", GROQ_MODEL),
        "last_attempt": LAST_GROQ_ATTEMPT,
    }


def _remember_attempt(success: bool, reason: str, attempted: bool = True) -> None:
    LAST_GROQ_ATTEMPT.update(
        {
            "attempted": attempted,
            "success": success,
            "reason": reason,
            "model": os.getenv("GROQ_MODEL", GROQ_MODEL),
        }
    )


def _decode_task_content(content: str):
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    values = []
    index = 0
    while index < len(content):
        while index < len(content) and content[index].isspace():
            index += 1
        if index >= len(content):
            break
        try:
            value, index = decoder.raw_decode(content, index)
            values.append(value)
        except json.JSONDecodeError:
            index += 1
    if values:
        return values

    start = content.find("[")
    end = content.rfind("]")
    if start != -1 and end != -1:
        return json.loads(content[start : end + 1])
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1:
        return json.loads(content[start : end + 1])
    raise json.JSONDecodeError("No JSON task content found", content, 0)


def _flatten_tasks(value) -> list[dict]:
    rows = []
    if isinstance(value, list):
        for item in value:
            rows.extend(_flatten_tasks(item))
        return rows
    if not isinstance(value, dict):
        return rows

    nested_tasks = value.get("tasks") or value.get("study_plan") or value.get("plan")
    if isinstance(nested_tasks, list):
        for task in nested_tasks:
            if isinstance(task, dict):
                rows.extend(
                    _flatten_tasks(
                        {
                            "day": task.get("day", value.get("day", "")),
                            "time_slot": task.get("time_slot", value.get("time_slot", "")),
                            "title": task.get("title", ""),
                            "description": task.get("description", ""),
                            "duration_minutes": task.get(
                                "duration_minutes",
                                value.get("duration_minutes", 30),
                            ),
                        }
                    )
                )
        return rows

    if value.get("title"):
        rows.append(value)
    return rows


def generate_groq_plan(profile: StudentProfile, strategy: str) -> list[dict] | None:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        _remember_attempt(False, "GROQ_API_KEY is not set.", attempted=False)
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
        "max_tokens": 3000,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You create topic-based learning roadmaps. Return ONLY valid JSON, no markdown. "
                    "Return one JSON object with a tasks array: {\"tasks\": [...]}. "
                    "The tasks array must cover the requested number of plan_days, with 3 or 4 task rows per day. "
                    "Each task object must have keys: "
                    "day, time_slot, title, description, duration_minutes. Use time_slot to store the day topic, "
                    "for example 'React - Timed Practice' or 'ML - Mistake Correction'. "
                    "Do not nest task rows inside day objects. "
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
            "Accept": "application/json",
            "User-Agent": "AI-Learning-Strategy/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="ignore")[:240]
        _remember_attempt(False, f"Groq HTTP {error.code}: {detail or error.reason}")
        return None
    except urllib.error.URLError as error:
        _remember_attempt(False, f"Groq connection failed: {error.reason}")
        return None
    except TimeoutError:
        _remember_attempt(False, "Groq request timed out.")
        return None
    except json.JSONDecodeError:
        _remember_attempt(False, "Groq returned a response that was not valid JSON.")
        return None

    content = payload.get("choices", [{}])[0].get("message", {}).get("content", "")
    try:
        tasks = _flatten_tasks(_decode_task_content(content))
    except json.JSONDecodeError:
        _remember_attempt(False, "Groq response task list could not be parsed.")
        return None

    if not isinstance(tasks, list) or len(tasks) < 14:
        _remember_attempt(False, "Groq response had too few task rows.")
        return None

    cleaned = []
    for task in tasks:
        if not isinstance(task, dict):
            _remember_attempt(False, "Groq response contained an invalid task row.")
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
    _remember_attempt(True, f"Groq generated {len(cleaned)} task rows.")
    return cleaned
