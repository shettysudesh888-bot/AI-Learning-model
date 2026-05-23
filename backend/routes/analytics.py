from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.models.entities import Feedback, Recommendation, StudentProfile, StudyTask, User
from backend.utils.security import get_current_user

router = APIRouter()


@router.get("/dashboard")
def dashboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).one()
    feedback = db.query(Feedback).filter(Feedback.user_id == current_user.id).order_by(Feedback.created_at.asc()).all()
    recommendations = (
        db.query(Recommendation)
        .filter(Recommendation.user_id == current_user.id)
        .order_by(Recommendation.created_at.desc())
        .limit(5)
        .all()
    )
    tasks = db.query(StudyTask).filter(StudyTask.user_id == current_user.id).order_by(StudyTask.id.asc()).all()
    completed_tasks = sum(task.completed for task in tasks)
    weak_areas = []
    if profile.quiz_scores < 65:
        weak_areas.append("Previous exam performance")
    if profile.target_score - profile.quiz_scores >= 15:
        weak_areas.append("Target score gap")
    if profile.weak_point:
        weak_areas.append(profile.weak_point)
    if profile.assignment_performance < 70:
        weak_areas.append("Assignment performance")
    if profile.attendance < 80:
        weak_areas.append("Attendance consistency")
    if profile.attention_span < 30:
        weak_areas.append("Sustained attention")

    weekly_improvement = [
        {
            "week": f"Week {index + 1}",
            "score": round(item.score_after if item.score_after else profile.quiz_scores, 1),
            "reward": item.reward,
        }
        for index, item in enumerate(feedback[-6:])
    ]
    if not weekly_improvement:
        weekly_improvement = [
            {"week": "Week 1", "score": max(profile.quiz_scores - 8, 0), "reward": 0},
            {"week": "Week 2", "score": max(profile.quiz_scores - 4, 0), "reward": 0},
            {"week": "Week 3", "score": profile.quiz_scores, "reward": 0},
        ]

    return {
        "profile": {
            "name": profile.name,
            "subjects": profile.subjects,
            "learning_style": profile.learning_style,
            "study_hours": profile.study_hours,
            "attention_span": profile.attention_span,
            "target_score": profile.target_score,
            "weak_point": profile.weak_point,
            "focus_topics": profile.focus_topics,
            "plan_days": profile.plan_days,
            "plan_mode": profile.plan_mode,
            "setup_completed": profile.setup_completed,
        },
        "performance": {
            "quiz_scores": profile.quiz_scores,
            "target_score": profile.target_score,
            "attendance": profile.attendance,
            "assignment_performance": profile.assignment_performance,
        },
        "weak_areas": weak_areas or ["No critical weak area detected"],
        "recent_recommendations": [
            {"id": row.id, "strategy": row.strategy, "confidence": row.confidence, "created_at": row.created_at}
            for row in recommendations
        ],
        "tasks": [
            {
                "id": task.id,
                "day": task.day,
                "time_slot": task.time_slot,
                "title": task.title,
                "description": task.description,
                "duration_minutes": task.duration_minutes,
                "completed": task.completed,
            }
            for task in tasks
        ],
        "task_completion": {
            "completed": completed_tasks,
            "total": len(tasks),
            "percent": round((completed_tasks / len(tasks)) * 100, 1) if tasks else 0,
        },
        "weekly_improvement": weekly_improvement,
        "average_reward": round(sum(item.reward for item in feedback) / len(feedback), 3) if feedback else 0,
    }


@router.get("/admin")
def admin_dashboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    students = db.query(StudentProfile).all()
    recommendations = db.query(Recommendation).all()
    feedback = db.query(Feedback).all()
    weak_students = [student for student in students if student.quiz_scores < 60 or student.target_score - student.quiz_scores >= 20]
    strategy_counts: dict[str, int] = {}
    for row in recommendations:
        strategy_counts[row.strategy] = strategy_counts.get(row.strategy, 0) + 1

    return {
        "total_students": len(students),
        "total_recommendations": len(recommendations),
        "total_feedback": len(feedback),
        "weak_students": [
            {
                "name": student.name,
                "subject": student.subjects,
                "score": student.quiz_scores,
                "target": student.target_score,
                "weak_point": student.weak_point,
            }
            for student in weak_students[:10]
        ],
        "strategy_counts": strategy_counts,
        "average_reward": round(sum(item.reward for item in feedback) / len(feedback), 3) if feedback else 0,
    }
