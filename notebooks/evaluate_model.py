from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

from train_model import load_training_data

ROOT_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT_DIR / "trained_models" / "random_forest_strategy.joblib"


def main() -> None:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Trained model not found at {MODEL_PATH}. Run notebooks/train_model.py first."
        )

    df = load_training_data()
    bundle = joblib.load(MODEL_PATH)
    model = bundle["model"]
    features = bundle.get("features", [column for column in df.columns if column != "strategy"])

    missing = [feature for feature in features if feature not in df.columns]
    if missing:
        raise ValueError(f"Dataset is missing model feature columns: {missing}")

    x = df[features]
    y = df["strategy"]
    _, x_test, _, y_test = train_test_split(
        x,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    predictions = model.predict(x_test)
    labels = sorted(y.unique())

    print("Model Evaluation")
    print("================")
    print(f"Model path: {MODEL_PATH}")
    print(f"Dataset rows: {len(df)}")
    print(f"Test rows: {len(x_test)}")
    print(f"Features: {', '.join(features)}")
    print(f"Accuracy: {accuracy_score(y_test, predictions):.4f}")
    print()

    print("Classification Report")
    print("---------------------")
    print(classification_report(y_test, predictions, labels=labels, zero_division=0))

    print("Confusion Matrix")
    print("----------------")
    matrix = confusion_matrix(y_test, predictions, labels=labels)
    matrix_df = pd.DataFrame(matrix, index=[f"actual: {label}" for label in labels], columns=[f"pred: {label}" for label in labels])
    print(matrix_df.to_string())


if __name__ == "__main__":
    main()
