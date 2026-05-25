"""
===============================================================================

    ML Model

    Carrega dois RandomForests persistidos
    (assets/models/{thermal,luminosity}.joblib) e expõe
    predict(SensorData) → Prediction (labels de conforto + confidences).

===============================================================================
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np

from pi_server.core.domain import (
    LuminosityComfort,
    Prediction,
    SensorData,
    ThermalComfort,
)

log = logging.getLogger(__name__)

_DEFAULT_MODELS_DIR = Path("assets/models")
_THERMAL_MODEL_FILE = "thermal.joblib"
_LUMINOSITY_MODEL_FILE = "luminosity.joblib"


def _load_bundle(path: Path) -> tuple[object, list[str]]:
    bundle = joblib.load(path)
    if not isinstance(bundle, dict) or "model" not in bundle or "features" not in bundle:
        raise ValueError(
            f"Bundle inválido em {path}; esperado dict com 'model' e 'features'."
        )
    return bundle["model"], bundle["features"]


def _feature_value(data: SensorData, name: str) -> float:
    match name:
        case "temperature":
            return data.dht11.temperature
        case "humidity":
            return data.dht11.humidity
        case "light_level":
            return float(data.light.light_level)
        case "hour_of_day":
            ts = data.timestamp or time.time()
            return float(datetime.fromtimestamp(ts).hour)
        case _:
            raise ValueError(f"Feature desconhecida: {name}")


def _build_row(data: SensorData, features: list[str]) -> np.ndarray:
    return np.array([[_feature_value(data, f) for f in features]], dtype=float)


def _confidence(model, row: np.ndarray, label: str) -> float | None:
    if not hasattr(model, "predict_proba"):
        return None
    proba = model.predict_proba(row)[0]
    classes = list(model.classes_)
    return float(proba[classes.index(label)])


@dataclass(slots=True)
class MLModel:
    _thermal_model: object = field(init=False)
    _thermal_features: list[str] = field(init=False)
    _luminosity_model: object = field(init=False)
    _luminosity_features: list[str] = field(init=False)

    def __init__(self, models_dir: Path | str = _DEFAULT_MODELS_DIR):
        models_dir = Path(models_dir)
        thermal_path = models_dir / _THERMAL_MODEL_FILE
        luminosity_path = models_dir / _LUMINOSITY_MODEL_FILE
        log.info(f"Loading ML models from {models_dir}")

        self._thermal_model, self._thermal_features = _load_bundle(thermal_path)
        self._luminosity_model, self._luminosity_features = _load_bundle(luminosity_path)

        log.info(
            f"Loaded thermal model (features={self._thermal_features}) "
            f"and luminosity model (features={self._luminosity_features})"
        )

    def predict(self, data: SensorData) -> Prediction:
        thermal_row = _build_row(data, self._thermal_features)
        luminosity_row = _build_row(data, self._luminosity_features)

        thermal_label = str(self._thermal_model.predict(thermal_row)[0])
        luminosity_label = str(self._luminosity_model.predict(luminosity_row)[0])

        thermal_conf = _confidence(self._thermal_model, thermal_row, thermal_label)
        luminosity_conf = _confidence(self._luminosity_model, luminosity_row, luminosity_label)

        log.debug(
            f"Predicted thermal={thermal_label} ({thermal_conf}), "
            f"luminosity={luminosity_label} ({luminosity_conf})"
        )

        return Prediction(
            thermal=ThermalComfort(thermal_label),
            luminosity=LuminosityComfort(luminosity_label),
            thermal_confidence=thermal_conf,
            luminosity_confidence=luminosity_conf,
        )
