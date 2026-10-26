"""Train and export the AGRIBORA classifier from the original crop dataset."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

FEATURES = ["Nitrogen", "Phosphorus", "Potassium", "Temperature", "Humidity", "pH_Value", "Rainfall"]
REQUIRED_COLUMNS = [*FEATURES, "Crop"]
DEFAULT_DATASET = Path(__file__).resolve().parent / "data" / "Crop_Recommendation.csv"
DEFAULT_MODEL_DIR = Path(__file__).resolve().parent / "models"


def load_dataset(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(
            f"Dataset not found: {path}\n"
            "Place the original Crop_Recommendation.csv at backend/data/ or pass --dataset."
        )

    frame = pd.read_csv(path)
    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    if missing_columns:
        raise ValueError(f"Dataset is missing required columns: {', '.join(missing_columns)}")

    frame = frame[REQUIRED_COLUMNS].copy().drop_duplicates()
    frame["Crop"] = frame["Crop"].astype("string").str.strip().str.lower()
    frame = frame.dropna(subset=["Crop"])
    frame.loc[:, FEATURES] = frame[FEATURES].apply(pd.to_numeric, errors="coerce")
    frame = frame.dropna(subset=FEATURES)

    finite_rows = frame[FEATURES].apply(lambda column: column.map(math.isfinite)).all(axis=1)
    frame = frame.loc[finite_rows]

    frame = frame[
        frame["Humidity"].between(0, 100)
        & frame["pH_Value"].between(0, 14)
        & (frame[["Nitrogen", "Phosphorus", "Potassium", "Rainfall"]] >= 0).all(axis=1)
    ]
    if frame.empty or frame["Crop"].nunique() < 2:
        raise ValueError("The cleaned dataset must contain samples for at least two crop labels.")
    if frame["Crop"].value_counts().min() < 2:
        raise ValueError("Each crop label needs at least two rows for a stratified train/test split.")
    if frame["Crop"].nunique() > int(len(frame) * 0.2):
        raise ValueError("The dataset needs enough rows for the stratified 20% test split.")

    return frame


def train(dataset_path: Path, model_dir: Path) -> None:
    frame = load_dataset(dataset_path)
    features = frame[FEATURES]
    encoder = LabelEncoder()
    labels = encoder.fit_transform(frame["Crop"])

    x_train, x_test, y_train, y_test = train_test_split(
        features,
        labels,
        test_size=0.2,
        random_state=42,
        stratify=labels,
    )
    classifier = RandomForestClassifier(n_estimators=100, random_state=42)
    classifier.fit(x_train, y_train)

    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(classifier, model_dir / "crop_rf_model.pkl")
    joblib.dump(encoder, model_dir / "label_encoder.pkl")

    accuracy = accuracy_score(y_test, classifier.predict(x_test))
    print(f"Trained on {len(frame)} rows across {len(encoder.classes_)} crop labels.")
    print(f"Held-out accuracy: {accuracy:.4f} (dataset split only; not a field-success guarantee).")
    print(f"Saved model and label encoder to {model_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET, help="Path to Crop_Recommendation.csv")
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR, help="Directory for exported artifacts")
    args = parser.parse_args()
    train(args.dataset, args.model_dir)


if __name__ == "__main__":
    main()
