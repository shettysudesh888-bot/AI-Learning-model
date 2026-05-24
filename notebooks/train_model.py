from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT_DIR = Path(__file__).resolve().parents[1]
NEW_DATASET_PATH = ROOT_DIR / "dataset" / "student_performance.csv"
LEGACY_DATASET_PATH = ROOT_DIR / "dataset" / "sample_students.csv"
MODEL_PATH = ROOT_DIR / "trained_models" / "random_forest_strategy.joblib"


def choose_strategy(row: pd.Series) -> str:
    if row["attention_span"] < 30 or row.get("stress_level", 0) >= 2:
        return "Pomodoro Technique"
    if row["quiz_scores"] < 55:
        return "Practice Quizzes"
    if row["attendance"] < 70:
        return "Revision Plans"
    if row["assignment_performance"] < 60:
        return "Notes"
    if row.get("final_grade", 0) >= 3 or row["quiz_scores"] >= 85:
        return "Mock Tests"
    if row["learning_style"] == "Visual":
        return "Concept Maps"
    if row["learning_style"] == "Audio":
        return "Video Tutorials"
    if row.get("discussions", 0) == 1 or row.get("extracurricular", 0) == 1:
        return "Group Study"
    return "Practice Quizzes"


def load_training_data() -> pd.DataFrame:
    if NEW_DATASET_PATH.exists():
        raw = pd.read_csv(NEW_DATASET_PATH)
        style_map = {0: "Visual", 1: "Reading", 2: "Practical", 3: "Audio"}
        normalized = pd.DataFrame(
            {
                "age": raw["Age"].astype(int),
                "education_level": raw["Age"].map(
                    lambda age: "High School" if age < 19 else "Undergraduate" if age < 25 else "Postgraduate"
                ),
                "learning_style": raw["LearningStyle"].map(style_map).fillna("Visual"),
                "study_hours": (raw["StudyHours"] / 7).clip(0.5, 8).round(1),
                "attention_span": (
                    25
                    + raw["Motivation"] * 12
                    + raw["Discussions"] * 8
                    + raw["Resources"] * 4
                    - raw["StressLevel"] * 7
                ).clip(15, 95).round().astype(int),
                "preferred_study_time": raw["StudyHours"].map(
                    lambda hours: "Morning" if hours >= 25 else "Evening" if hours >= 15 else "Night"
                ),
                "quiz_scores": raw["ExamScore"].astype(float),
                "attendance": raw["Attendance"].astype(float),
                "assignment_performance": raw["AssignmentCompletion"].astype(float),
                "stress_level": raw["StressLevel"],
                "final_grade": raw["FinalGrade"],
                "discussions": raw["Discussions"],
                "extracurricular": raw["Extracurricular"],
            }
        )
        normalized["strategy"] = normalized.apply(choose_strategy, axis=1)
        return normalized.drop(columns=["stress_level", "final_grade", "discussions", "extracurricular"])

    if LEGACY_DATASET_PATH.exists():
        return pd.read_csv(LEGACY_DATASET_PATH)

    raise FileNotFoundError("No dataset found. Add dataset/student_performance.csv or run notebooks/generate_dataset.py.")


def main() -> None:
    df = load_training_data()
    target = "strategy"
    features = [column for column in df.columns if column != target]
    categorical = ["education_level", "learning_style", "preferred_study_time"]
    numeric = [column for column in features if column not in categorical]

    preprocessor = ColumnTransformer(
        transformers=[
            ("categorical", OneHotEncoder(handle_unknown="ignore"), categorical),
            ("numeric", StandardScaler(), numeric),
        ]
    )
    model = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", RandomForestClassifier(n_estimators=180, random_state=42, class_weight="balanced")),
        ]
    )

    print(f"Training rows: {len(df)}")
    print("Strategy distribution:")
    print(df[target].value_counts().to_string())

    x_train, x_test, y_train, y_test = train_test_split(df[features], df[target], test_size=0.2, random_state=42, stratify=df[target])
    model.fit(x_train, y_train)
    predictions = model.predict(x_test)
    print(classification_report(y_test, predictions))

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "features": features}, MODEL_PATH)
    print(f"Saved {MODEL_PATH}")


if __name__ == "__main__":
    main()
