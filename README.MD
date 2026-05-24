# AI-Based Personalized Learning Strategy Recommendation System

Full-stack AI learning assistant that recommends personalized study strategies from student goals, previous exam score, target score, weak point, learning preference, and feedback. The backend uses FastAPI, a Random Forest recommendation model, and a simple Q-Learning layer that adapts future recommendations from student outcomes.

## Tech Stack

- Frontend: HTML, CSS, JavaScript served by FastAPI
- Backend: FastAPI, SQLAlchemy, JWT authentication
- Database: SQLite by default, MySQL-ready through `DATABASE_URL`
- ML: scikit-learn, pandas, NumPy, joblib
- RL: lightweight Q-Learning table persisted as JSON

## Project Structure

```text
backend/
  app.py
  database/
  models/
  recommendation_engine/
  rl_agent/
  routes/
  utils/
dataset/
  student_performance.csv
frontend/
  index.html
notebooks/
  generate_dataset.py
  train_model.py
trained_models/
screenshots/
```

## Backend Setup

```powershell
cd "C:\AI Learning Strategy"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
python notebooks\train_model.py
uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

Optional MySQL:

```powershell
$env:DATABASE_URL="mysql+pymysql://user:password@localhost:3306/ai_learning_strategy"
```

## Frontend Setup

No separate frontend server is required. Start the FastAPI backend:

```powershell
cd "C:\AI Learning Strategy"
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/app`. The frontend is `frontend/index.html`, and it calls the backend API on the same FastAPI server.

## Demo Login

After backend startup, create a Student or Admin account on the register page. Student accounts use the guided setup flow. Admin accounts can view platform analytics and weak students. Students can add one or more subjects to their profile. They can also enter optional focus topics, choose the plan length, and select a plan mode: full-subject improvement, focus-topic improvement, exam revision, or mock-test practice. When multiple subjects are saved, the recommendation screen creates a separate plan for each subject, and the student can click a subject tab to view that plan.

## Dataset Notes

The trainer prefers `dataset/student_performance.csv` when present. That file is normalized into the backend feature schema and strategy labels are derived from performance, stress level, attendance, assignment completion, final grade, and learning style. If that file is missing, the trainer falls back to `dataset/sample_students.csv`, which can be generated with `python notebooks\generate_dataset.py`.

## API Highlights

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/profile/me`
- `PUT /api/profile/me`
- `POST /api/recommendations`
- `GET /api/recommendations/history`
- `POST /api/feedback`
- `GET /api/analytics/dashboard`

## AI Workflow

1. Student profile and performance data are saved.
2. Student enters previous score, target score, weak point, study availability, and learning preference.
3. Random Forest predicts a base learning strategy.
4. Q-Learning adjusts the strategy using previous rewards for similar student states.
5. Student receives a recommendation plus a subject-wise improvement plan for the selected number of days.
6. Student feedback and score improvement become reward signals.
7. Future recommendations adapt dynamically.
