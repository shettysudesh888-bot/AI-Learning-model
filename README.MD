# AI-Based Personalized Learning Strategy Recommendation System

![AI Learning Strategy Banner](screenshots/banner.png)

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](https://opensource.org/licenses/MIT)
## 👨‍💻 Connect With Me

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Sudesh%20S%20Shetty-blue?style=for-the-badge&logo=linkedin)](https://www.linkedin.com/in/sudesh-s-shetty-061838319)

[![GitHub](https://img.shields.io/badge/GitHub-shettysudesh888--bot-black?style=for-the-badge&logo=github)](https://github.com/shettysudesh888-bot)

A state-of-the-art, full-stack AI learning assistant designed to recommend personalized study strategies. By analyzing key student characteristics—such as exam scores, learning preferences, study duration availability, attention spans, and weak points—the system generates tailored study schedules. The recommendation engine integrates a **Random Forest Classifier** for baseline recommendations and a **Q-Learning (Reinforcement Learning)** agent to dynamically refine and adapt strategies based on real student outcomes and feedback.

---

## 🌟 Key Features

### 👤 Student Profile & Preferences Wizard
*   Guided registration and onboarding setup.
*   Support for multiple subjects (e.g., Mathematics, Science) with separate active plans per subject.
*   Profile details including attention span, weekly study hours, preferred times, and weak areas.

### 🤖 Hybrid AI Recommendation Engine
*   **Predictive Model:** Random Forest pipeline to classify students into optimal baseline learning strategy types.
*   **Reinforcement Learning:** Persistent Q-Learning table to adapt future strategy recommendations from reward signals (user feedback, rating, score improvement).
*   **Diverse Strategies:** Recommends Pomodoro Technique, Practice Quizzes, Concept Maps, Revision Plans, Mock Tests, Video Tutorials, Cornell Notes, or Group Study.

### 📅 Subject-Wise Study Planners
*   Generates customized schedules for selected intervals (e.g., 7 days, 14 days, 30 days).
*   Supports different plan modes: *Full-Subject Improvement*, *Focus-Topic Improvement*, *Exam Revision*, or *Mock-Test Practice*.
*   Export study schedules directly to a professional PDF layout.

### 📊 Admin & Analytics Dashboard
*   Platform-wide analytics for administrators to track metrics.
*   Detailed list of student weak points and targeted recommendation logs.
*   Progress charts, attendance statistics, and learning style distributions.

---

## 🏗️ Architecture & Workflow

```mermaid
graph TD
    A[Student Profile & Input Data] --> B[Random Forest Engine]
    B -->|Predictive Baseline| C[Q-Learning Agent]
    C -->|Choose Action: Explore / Exploit| D[Final Study Strategy]
    D --> E[Day-by-Day Study Schedule & PDF Export]
    E --> F[Student Progress & Feedback Loop]
    F -->|Calculate Reward| G[Update Q-Table]
    G -->|Continuous Optimization| C
```

### 🧠 The AI Workflow in Detail

1. **Feature Vector Extraction:** When a student requests a study plan, their profile is mapped to the following feature vector:
   $$\text{Features} = \begin{bmatrix} \text{Age}, \text{Education Level}, \text{Learning Style}, \text{Study Hours}, \text{Attention Span}, \text{Preferred Time}, \text{Quiz Score}, \text{Attendance}, \text{Assignment Perf} \end{bmatrix}$$
2. **Random Forest Prediction:** The scikit-learn classifier pipeline runs preprocessing (StandardScaler + OneHotEncoder) and predicts the best baseline strategy with a probability/confidence score.
3. **Q-Learning Adaptation:** 
   * The agent constructs a state key string: `f"{score_level}:{attention_level}:{study_hours}:{learning_style}"`.
   * With probability $\epsilon$ (exploration rate), a random strategy is chosen. Otherwise, the agent selects the action with the highest Q-value from the Q-table (`trained_models/q_table.json`). If no positive reinforcement exists yet, it defaults to the Random Forest baseline.
4. **Reward Formulation:** When a student completes a plan, they provide feedback (rating $1\text{--}5$, a boolean indicating if it helped, and before/after exam scores). The reward $R$ is calculated as:
   $$R = \frac{\text{Rating} - 3}{2} + \text{Improvement Component} + \text{Help Component}$$
   Where the *Improvement Component* is the clamped score difference: $\text{clip}\left(\frac{\text{Score}_{\text{after}} - \text{Score}_{\text{before}}}{20}, -1.0, 1.0\right)$ and the *Help Component* is $+0.4$ for positive help and $-0.4$ otherwise.
5. **Q-Value Update (Temporal Difference):**
   $$Q(s, a) \leftarrow Q(s, a) + \alpha \left[ R + \gamma \max_{a'} Q(s', a') - Q(s, a) \right]$$

---

## 📁 Project Structure

```text
├── backend/
│   ├── database/
│   │   └── session.py                 # SQLite/MySQL SQLAlchemy engine config
│   ├── models/
│   │   └── entities.py                # Database models (User, Profile, etc.)
│   ├── recommendation_engine/
│   │   ├── engine.py                  # Random Forest predictions & resources
│   │   └── groq_plan.py               # (Optional) LLM-based plan enhancer
│   ├── rl_agent/
│   │   └── q_learning.py              # Reinforcement learning agent & reward logic
│   ├── routes/
│   │   ├── analytics.py               # Platform analytics and admin dashboard endpoints
│   │   ├── auth.py                    # User authentication & registration
│   │   ├── feedback.py                # Q-learning feedback & rewards endpoint
│   │   ├── profile.py                 # Student profile CRUD
│   │   ├── recommendations.py         # Study plan generator & PDF compiler
│   │   └── tasks.py                   # Calendar task tracking
│   ├── utils/
│   │   └── security.py                # password hashing & JWT token validation
│   ├── app.py                         # FastAPI App startup entrypoint
│   ├── requirements.txt               # Backend Python dependencies
│   └── schemas.py                     # Pydantic validation schemas
├── dataset/
│   ├── student_performance.csv        # Core training dataset (if present)
│   └── sample_students.csv            # Simulated training dataset (fallback)
├── frontend/
│   └── index.html                     # Glassmorphic single-page web app
├── notebooks/
│   ├── generate_dataset.py            # Script to simulate student demographic data
│   ├── train_model.py                 # Training script for Random Forest classifier
│   └── evaluate_model.py              # Evaluates accuracy & prints classification reports
├── trained_models/
│   ├── random_forest_strategy.joblib  # Trained scikit-learn model artifact
│   └── q_table.json                   # Persisted RL Q-learning database
└── screenshots/
    └── banner.png                     # Generated README header banner
```

---

## 🗄️ Database Schema

The database contains five relational tables. SQLite is configured by default, and can be switched to MySQL via the `DATABASE_URL` environment variable.

| Table Name | Entity Class | Primary Key | Keys / Relationships | Key Columns & Types |
| :--- | :--- | :--- | :--- | :--- |
| **`users`** | `User` | `id` (INT) | Profile (`1:1`), Recommendations (`1:N`), Feedback (`1:N`), Tasks (`1:N`) | `email` (VARCHAR, Unique), `password_hash` (VARCHAR), `role` (VARCHAR) |
| **`student_profiles`** | `StudentProfile` | `id` (INT) | ForeignKey: `user_id` $\rightarrow$ `users.id` | `name`, `age`, `learning_style`, `subjects`, `quiz_scores`, `target_score`, `weak_point`, `attendance`, `assignment_performance` |
| **`recommendations`** | `Recommendation` | `id` (INT) | ForeignKey: `user_id` $\rightarrow$ `users.id`, Feedback (`1:1`) | `strategy` (VARCHAR), `confidence` (FLOAT), `resources` (TEXT/JSON), `rationale` (TEXT), `state_key` (VARCHAR) |
| **`feedback`** | `Feedback` | `id` (INT) | ForeignKey: `user_id`, `recommendation_id` | `rating` (INT), `helped` (INT), `score_before` (FLOAT), `score_after` (FLOAT), `reward` (FLOAT), `comments` |
| **`study_tasks`** | `StudyTask` | `id` (INT) | ForeignKey: `user_id`, `recommendation_id` | `day` (VARCHAR), `time_slot` (VARCHAR), `title` (VARCHAR), `description` (TEXT), `duration_minutes` (INT), `completed` (INT) |

---

## 🚀 Getting Started

### Prerequisites
*   Python 3.10 or higher
*   pip package manager

### 1. Installation

Clone the repository and set up a Python virtual environment:

```powershell
# Navigate to the project directory
cd "c:\AI Learning Strategy"

# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# Install required dependencies
pip install -r backend/requirements.txt
```

### 2. Dataset Generation & Model Training

If you don't have the primary dataset `dataset/student_performance.csv` placed, run the dataset generator script first. Then, train the Random Forest classification model:

```powershell
# Optional: Generate simulated student dataset
python notebooks/generate_dataset.py

# Train the Random Forest recommendation model
python notebooks/train_model.py
```
*This will create the pretrained classifier in `trained_models/random_forest_strategy.joblib`.*

### 3. Database & App Startup

Launch the FastAPI backend server:

```powershell
# Start server in development mode (with hot-reload)
uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

*   **API Interactive Documentation (Swagger UI):** Visit [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
*   **Web Application Interface:** Open [http://127.0.0.1:8000/app](http://127.0.0.1:8000/app) in your browser.

---

## 📡 API Reference Highlights

### Authentication
*   `POST /api/auth/register` - Create new student or administrator accounts.
*   `POST /api/auth/login` - Authenticate users and return access JWT tokens.

### Profiles
*   `GET /api/profile/me` - Fetch profile parameters of the logged-in student.
*   `PUT /api/profile/me` - Update subject choices, learning style, and study target parameters.

### Recommendations & Feedback
*   `POST /api/recommendations` - Run Random Forest + RL model to generate a new study schedule.
*   `GET /api/recommendations/history` - Retrieve historical recommendation history.
*   `GET /api/recommendations/{recommendation_id}/pdf` - Download a study guide PDF report.
*   `POST /api/feedback` - Submit student feedback post-study and trigger Q-Learning Q-table updates.

### Analytics (Admin)
*   `GET /api/analytics/dashboard` - Get key platform KPIs, weak student tracking lists, and class averages.

---

## ⚙️ Configuration

Set custom database environments or token variables in a local `.env` file in the root directory:

```env
DATABASE_URL=sqlite:///c:/AI Learning Strategy/learning_strategy.db
# Or use external MySQL database:
# DATABASE_URL=mysql+pymysql://db_user:db_password@localhost:3306/ai_learning_strategy

SECRET_KEY=your-highly-secure-jwt-secret-key-string
```

---

## 📝 License

Distributed under the MIT License. See [LICENSE](LICENSE) for more details.
