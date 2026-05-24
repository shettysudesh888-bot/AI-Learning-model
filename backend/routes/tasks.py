from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.models.entities import StudyTask, User
from backend.schemas import StudyTaskResponse, StudyTaskUpdate
from backend.utils.security import get_current_user

router = APIRouter()


@router.get("", response_model=list[StudyTaskResponse])
def list_tasks(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(StudyTask)
        .filter(StudyTask.user_id == current_user.id)
        .order_by(StudyTask.id.asc())
        .all()
    )


@router.patch("/{task_id}", response_model=StudyTaskResponse)
def update_task(
    task_id: int,
    payload: StudyTaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = db.query(StudyTask).filter(StudyTask.id == task_id, StudyTask.user_id == current_user.id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    task.completed = 1 if payload.completed else 0
    db.commit()
    db.refresh(task)
    return task
