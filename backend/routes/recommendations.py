import re
import textwrap

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.models.entities import Feedback, Recommendation, StudentProfile, StudyTask, User
from backend.recommendation_engine.engine import (
    build_recommendation_payload,
    decode_resources,
    encode_resources,
    predict_strategy,
    state_key,
)
from backend.recommendation_engine.groq_plan import generate_groq_plan, groq_status
from backend.rl_agent.q_learning import QLearningAgent
from backend.schemas import RecommendationResponse
from backend.utils.security import get_current_user

router = APIRouter()


@router.get("/llm-status")
def llm_status():
    return groq_status()


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


def _subjects_from_tasks(tasks: list[StudyTask]) -> list[str]:
    subjects = []
    for task in tasks:
        if " - " not in task.time_slot:
            continue
        subject = task.time_slot.split(" - ", 1)[0].strip()
        if subject and not any(item.lower() == subject.lower() for item in subjects):
            subjects.append(subject)
    return subjects


def _pdf_text(value: object) -> str:
    return str(value).encode("latin-1", errors="replace").decode("latin-1")


def _pdf_escape(value: object) -> str:
    return _pdf_text(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_study_plan_pdf(row: Recommendation, tasks: list[StudyTask]) -> bytes:
    lines = [
        "Learnova AI Study Plan",
        "",
        f"Strategy: {row.strategy}",
        f"Confidence: {round(row.confidence * 100)}%",
        f"Created: {row.created_at.strftime('%Y-%m-%d')}",
        "",
        "Rationale:",
    ]
    lines.extend(textwrap.wrap(row.rationale, width=92) or [""])
    lines.extend(["", "Study Tasks:"])

    current_day = None
    for task in tasks:
        if task.day != current_day:
            current_day = task.day
            lines.extend(["", _pdf_text(task.day)])
        title = f"- {task.time_slot + ' - ' if task.time_slot else ''}{task.title} ({task.duration_minutes} min)"
        lines.extend(textwrap.wrap(title, width=92, subsequent_indent="  "))
        if task.description:
            lines.extend(textwrap.wrap(f"  {task.description}", width=92, subsequent_indent="  "))

    pages = []
    page_lines = []
    for line in lines:
        if len(page_lines) >= 44:
            pages.append(page_lines)
            page_lines = []
        page_lines.append(line)
    if page_lines:
        pages.append(page_lines)

    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [" + " ".join(f"{3 + index * 2} 0 R" for index in range(len(pages))) + f"] /Count {len(pages)} >>",
    ]

    for index, page in enumerate(pages):
        page_object_id = 3 + index * 2
        stream_object_id = page_object_id + 1
        stream_lines = ["BT", "/F1 12 Tf", "50 770 Td", "16 TL"]
        for line_number, line in enumerate(page):
            if line_number:
                stream_lines.append("T*")
            stream_lines.append(f"({_pdf_escape(line)}) Tj")
        stream_lines.append("ET")
        stream = "\n".join(stream_lines)
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /Contents {stream_object_id} 0 R >>")
        objects.append(f"<< /Length {len(stream.encode('latin-1'))} >>\nstream\n{stream}\nendstream")

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for object_id, content in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{object_id} 0 obj\n{content}\nendobj\n".encode("latin-1"))
    xref_at = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("latin-1"))
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
    pdf.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode("latin-1"))
    return bytes(pdf)


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
    if len(subjects) > 1:
        fallback_source = "Local fallback (Groq skipped for multiple subjects)"
    else:
        fallback_source = f"Local fallback ({groq_status()['last_attempt']['reason']})"

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
        fallback_source,
    )


def _to_response(row: Recommendation) -> RecommendationResponse:
    source_match = re.search(
        r"Study plan source: (.+)\.$",
        row.rationale
    )

    plan_source = (
        "Groq LLM"
        if "Study plan source: Groq LLM" in row.rationale
        else "Local fallback"
    )

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
        plan_source=plan_source,
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


@router.get("/{recommendation_id}/pdf")
def download_recommendation_pdf(
    recommendation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = (
        db.query(Recommendation)
        .filter(Recommendation.id == recommendation_id, Recommendation.user_id == current_user.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    tasks = (
        db.query(StudyTask)
        .filter(StudyTask.recommendation_id == row.id, StudyTask.user_id == current_user.id)
        .order_by(StudyTask.id.asc())
        .all()
    )
    filename = f"study-plan-{row.id}.pdf"
    return Response(
        content=_build_study_plan_pdf(row, tasks),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{recommendation_id}")
def delete_recommendation(
    recommendation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = (
        db.query(Recommendation)
        .filter(Recommendation.id == recommendation_id, Recommendation.user_id == current_user.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    profile = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).one()
    deleted_tasks = (
        db.query(StudyTask)
        .filter(StudyTask.recommendation_id == row.id, StudyTask.user_id == current_user.id)
        .all()
    )
    deleted_subjects = _subjects_from_tasks(deleted_tasks)

    db.query(StudyTask).filter(
        StudyTask.recommendation_id == row.id,
        StudyTask.user_id == current_user.id,
    ).delete(synchronize_session=False)
    db.query(Feedback).filter(
        Feedback.recommendation_id == row.id,
        Feedback.user_id == current_user.id,
    ).delete(synchronize_session=False)
    db.delete(row)
    remaining_count = (
        db.query(Recommendation)
        .filter(Recommendation.user_id == current_user.id, Recommendation.id != row.id)
        .count()
    )
    if deleted_subjects:
        remaining_subjects = [
            subject
            for subject in _split_subjects(profile.subjects)
            if not any(subject.lower() == deleted.lower() for deleted in deleted_subjects)
        ]
        profile.subjects = ", ".join(remaining_subjects)
    elif remaining_count == 0:
        profile.subjects = ""
    db.commit()
    return {"message": "Study plan deleted", "deleted_subjects": deleted_subjects}
