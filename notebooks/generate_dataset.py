from pathlib import Path

import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT_DIR / "dataset" / "sample_students.csv"

LEARNING_STYLES = ["Visual", "Reading", "Practical", "Audio"]
EDUCATION_LEVELS = ["High School", "Undergraduate", "Diploma", "Postgraduate"]
STUDY_TIMES = ["Morning", "Afternoon", "Evening", "Night"]


def choose_strategy(row: dict) -> str:
    if row["attention_span"] < 30:
        return "Pomodoro Technique"
    if row["quiz_scores"] < 55:
        return "Practice Quizzes"
    if row["attendance"] < 70:
        return "Revision Plans"
    if row["assignment_performance"] < 60:
        return "Notes"
    if row["quiz_scores"] > 82 and row["assignment_performance"] > 80:
        return "Mock Tests"
    if row["learning_style"] == "Visual":
        return "Concept Maps"
    if row["learning_style"] == "Audio":
        return "Video Tutorials"
    if row["study_hours"] >= 3.5:
        return "Group Study"
    return "Practice Quizzes"


def main(rows: int = 600) -> None:
    rng = np.random.default_rng(42)
    records = []
    for _ in range(rows):
        record = {
            "age": int(rng.integers(13, 28)),
            "education_level": rng.choice(EDUCATION_LEVELS),
            "learning_style": rng.choice(LEARNING_STYLES),
            "study_hours": round(float(rng.uniform(0.5, 6.0)), 1),
            "attention_span": int(rng.integers(15, 95)),
            "preferred_study_time": rng.choice(STUDY_TIMES),
            "quiz_scores": round(float(np.clip(rng.normal(70, 16), 20, 100)), 1),
            "attendance": round(float(np.clip(rng.normal(82, 13), 35, 100)), 1),
            "assignment_performance": round(float(np.clip(rng.normal(72, 15), 25, 100)), 1),
        }
        record["strategy"] = choose_strategy(record)
        records.append(record)

    DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(records).to_csv(DATASET_PATH, index=False)
    print(f"Generated {DATASET_PATH}")


if __name__ == "__main__":
    main()
