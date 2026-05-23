# 🎓 AI-Based Personalized Learning Strategy Recommendation System

An intelligent full-stack learning platform that generates personalized study strategies for students using Machine Learning and Reinforcement Learning techniques.

The system analyzes student performance, learning preferences, target goals, weak areas, and previous scores to generate customized study plans and continuously improve recommendations through feedback.

---

## 🚀 Features

- User Authentication (Student/Admin login)
- Personalized study strategy recommendations
- AI-based prediction using Random Forest
- Adaptive recommendations using Q-Learning
- Subject-wise learning plans
- Performance analytics dashboard
- Student profile management
- Feedback-based learning improvement
- Multiple learning modes:
  - Full Subject Improvement
  - Focus Topic Improvement
  - Exam Revision
  - Mock Test Practice

---

## 🛠 Tech Stack

### Frontend
- HTML
- CSS
- JavaScript

### Backend
- FastAPI
- SQLAlchemy
- JWT Authentication

### Database
- SQLite
- MySQL (optional)

### Machine Learning
- Scikit-learn
- Pandas
- NumPy
- Joblib

### AI Techniques
- Random Forest
- Q-Learning

---

## 📁 Project Structure

```text
AI-Learning-Model/
│
├── backend/
├── frontend/
├── dataset/
├── notebooks/
├── trained_models/
├── models/
├── screenshots/
├── README.md
└── .gitignore
```

---

## ⚙️ Installation

### Clone repository

```bash
git clone https://github.com/yourusername/AI-Learning-model.git
cd AI-Learning-model
```

### Create virtual environment

```bash
python -m venv .venv
```

### Activate environment

Windows:

```bash
.\.venv\Scripts\activate
```

### Install dependencies

```bash
pip install -r backend/requirements.txt
```

### Train model

```bash
python notebooks/train_model.py
```

### Run application

```bash
uvicorn backend.app:app --reload
```

---

## 🌐 Access Application

Open:

```text
http://127.0.0.1:8000/app
```

---

## 🔄 Working Flow

1. User registers and logs in
2. Student enters:
   - Previous score
   - Target score
   - Weak areas
   - Learning preference
   - Available study time

3. Random Forest predicts a learning strategy

4. Q-Learning improves recommendations based on previous outcomes

5. Personalized study plans are generated

6. Feedback updates future recommendations

---

## 📊 API Endpoints

| Method | Endpoint |
|----------|-----------|
| POST | /api/auth/register |
| POST | /api/auth/login |
| GET | /api/profile/me |
| PUT | /api/profile/me |
| POST | /api/recommendations |
| GET | /api/recommendations/history |
| POST | /api/feedback |
| GET | /api/analytics/dashboard |

---

## 🔮 Future Enhancements

- Real-time progress tracking
- AI chatbot assistance
- Mobile application support
- Cloud deployment
- Deep learning recommendation models
- Integration with LMS platforms

---

## 👨‍💻 Developed By

Sudesh S Shetty

---

⭐ If you like this project, give it a star.
