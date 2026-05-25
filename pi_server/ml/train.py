"""
===============================================================================

    Train two RandomForest classifiers (thermal + luminosity comfort) and
    persist as joblib bundles.

    Uso:
        uv run -m pi_server.ml.train

===============================================================================
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier

# Features de cada modelo. Mantidas em constantes para o ml_model.py reusar
# e garantir consistência entre treino e inferência.
THERMAL_FEATURES:    list[str] = ["temperature", "humidity"]
LUMINOSITY_FEATURES: list[str] = ["light_level", "hour_of_day"]


@dataclass(slots=True)
class TrainedModel:
    name: str
    model: RandomForestClassifier
    accuracy: float
    baseline_accuracy: float
    report: str
    confusion: np.ndarray
    classes: list[str]


def _train_one(
    df: pd.DataFrame,
    features: list[str],
    target: str,
    name: str,
    seed: int,
) -> TrainedModel:
    X = df[features].to_numpy()
    y = df[target].to_numpy()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=seed, stratify=y
    )

    rf = RandomForestClassifier(
        n_estimators=100,
        max_depth=8,
        random_state=seed,
        n_jobs=-1,
    )
    rf.fit(X_train, y_train)
    y_pred = rf.predict(X_test)
    rf_acc = accuracy_score(y_test, y_pred)

    # Baseline: DecisionTree pequena, para comparação no relatório
    dt = DecisionTreeClassifier(max_depth=4, random_state=seed)
    dt.fit(X_train, y_train)
    dt_acc = accuracy_score(y_test, dt.predict(X_test))

    return TrainedModel(
        name=name,
        model=rf,
        accuracy=rf_acc,
        baseline_accuracy=dt_acc,
        report=classification_report(y_test, y_pred, zero_division=0),
        confusion=confusion_matrix(y_test, y_pred, labels=rf.classes_),
        classes=list(rf.classes_),
    )


def _print_results(tm: TrainedModel) -> None:
    print(f"\n=== {tm.name} ===")
    print(f"RandomForest accuracy: {tm.accuracy:.4f}")
    print(f"DecisionTree baseline: {tm.baseline_accuracy:.4f}")
    print("\nClassification report:")
    print(tm.report)
    print("Confusion matrix (rows=true, cols=pred):")
    header = "          " + "  ".join(f"{c:>10}" for c in tm.classes)
    print(header)
    for cls, row in zip(tm.classes, tm.confusion):
        print(f"{cls:>10}  " + "  ".join(f"{v:>10d}" for v in row))


def train_all(dataset_path: Path, models_dir: Path, seed: int = 42) -> None:
    df = pd.read_csv(dataset_path)
    print(f"Loaded {len(df)} samples from {dataset_path}")

    thermal = _train_one(
        df, THERMAL_FEATURES, "thermal_comfort", "Thermal comfort classifier", seed
    )
    luminosity = _train_one(
        df, LUMINOSITY_FEATURES, "luminosity_comfort", "Luminosity comfort classifier", seed
    )

    _print_results(thermal)
    _print_results(luminosity)

    models_dir.mkdir(parents=True, exist_ok=True)
    thermal_path = models_dir / "thermal.joblib"
    luminosity_path = models_dir / "luminosity.joblib"

    # Empacotar metadata junto com o estimador para o loader saber as features
    joblib.dump({"model": thermal.model, "features": THERMAL_FEATURES}, thermal_path)
    joblib.dump({"model": luminosity.model, "features": LUMINOSITY_FEATURES}, luminosity_path)

    print(f"\nSaved thermal model    → {thermal_path}")
    print(f"Saved luminosity model → {luminosity_path}")


def main():
    parser = argparse.ArgumentParser(description="Treina classificadores de conforto.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("assets/dataset.csv"),
    )
    parser.add_argument(
        "--models-dir",
        type=Path,
        default=Path("assets/models"),
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    train_all(args.dataset, args.models_dir, args.seed)


if __name__ == "__main__":
    main()
