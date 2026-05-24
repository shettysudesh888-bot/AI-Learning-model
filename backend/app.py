from pathlib import Path
<<<<<<< HEAD
import os
=======
>>>>>>> d72f55f2f2e33a3d35d5920d3f2ac83012399b4b
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

<<<<<<< HEAD

def load_local_env() -> None:
    env_path = ROOT_DIR / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_local_env()

=======
>>>>>>> d72f55f2f2e33a3d35d5920d3f2ac83012399b4b
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import inspect, text

from backend.database.session import Base, engine
from backend.routes import analytics, auth, feedback, profile, recommendations, tasks

app = FastAPI(title="AI Learning Strategy API", version="1.0.0")
STATIC_DIR = ROOT_DIR / "frontend"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "null"],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)


def ensure_schema() -> None:
    inspector = inspect(engine)
    with engine.begin() as connection:
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        if "role" not in user_columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'student'"))
        connection.execute(text("UPDATE users SET role = 'student' WHERE role IS NULL OR role = ''"))
        profile_columns = {column["name"] for column in inspector.get_columns("student_profiles")}
        if "target_score" not in profile_columns:
            connection.execute(text("ALTER TABLE student_profiles ADD COLUMN target_score FLOAT DEFAULT 80.0"))
        if "weak_point" not in profile_columns:
            connection.execute(text("ALTER TABLE student_profiles ADD COLUMN weak_point VARCHAR(80) DEFAULT 'Problem solving'"))
        if "focus_topics" not in profile_columns:
            connection.execute(text("ALTER TABLE student_profiles ADD COLUMN focus_topics TEXT DEFAULT ''"))
        if "plan_days" not in profile_columns:
            connection.execute(text("ALTER TABLE student_profiles ADD COLUMN plan_days INTEGER DEFAULT 7"))
        if "plan_mode" not in profile_columns:
            connection.execute(text("ALTER TABLE student_profiles ADD COLUMN plan_mode VARCHAR(40) DEFAULT 'improvement'"))
        if "setup_completed" not in profile_columns:
            connection.execute(text("ALTER TABLE student_profiles ADD COLUMN setup_completed INTEGER DEFAULT 0"))
        task_columns = {column["name"] for column in inspector.get_columns("study_tasks")} if "study_tasks" in inspector.get_table_names() else set()
        if task_columns and "time_slot" not in task_columns:
            connection.execute(text("ALTER TABLE study_tasks ADD COLUMN time_slot VARCHAR(40) DEFAULT ''"))


ensure_schema()

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(profile.router, prefix="/api/profile", tags=["profile"])
app.include_router(recommendations.router, prefix="/api/recommendations", tags=["recommendations"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["feedback"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])


@app.get("/")
def health_check():
    return {"status": "ok", "service": "AI Learning Strategy API"}


@app.get("/app", include_in_schema=False)
def web_app():
    return FileResponse(STATIC_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000, reload=True)
