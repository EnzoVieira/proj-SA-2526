"""
===============================================================================

    ML Model

    Carrega dois RandomForests persistidos (assets/models/{ac,blinds}.joblib)
    e expõe predict(SensorData) → Prediction.

===============================================================================
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import joblib
import numpy as np

from pi_server.core.domain import (
    ACAction,
    BlindsAction,
    Prediction,
    SensorData,
)

log = logging.getLogger(__name__)

_DEFAULT_MODELS_DIR = Path("assets/models")
_AC_MODEL_FILE = "ac.joblib"
_BLINDS_MODEL_FILE = "blinds.joblib"


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
    _ac_model: object = field(init=False)
    _ac_features: list[str] = field(init=False)
    _blinds_model: object = field(init=False)
    _blinds_features: list[str] = field(init=False)

    def __init__(self, models_dir: Path | str = _DEFAULT_MODELS_DIR):
        models_dir = Path(models_dir)
        ac_path = models_dir / _AC_MODEL_FILE
        blinds_path = models_dir / _BLINDS_MODEL_FILE
        log.info(f"Loading ML models from {models_dir}")

        self._ac_model, self._ac_features = _load_bundle(ac_path)
        self._blinds_model, self._blinds_features = _load_bundle(blinds_path)

        log.info(
            f"Loaded AC model (features={self._ac_features}) "
            f"and Blinds model (features={self._blinds_features})"
        )

    def predict(self, data: SensorData) -> Prediction:
        ac_row = _build_row(data, self._ac_features)
        blinds_row = _build_row(data, self._blinds_features)

        ac_label = str(self._ac_model.predict(ac_row)[0])
        blinds_label = str(self._blinds_model.predict(blinds_row)[0])

        ac_conf = _confidence(self._ac_model, ac_row, ac_label)
        blinds_conf = _confidence(self._blinds_model, blinds_row, blinds_label)

        log.debug(
            f"Predicted ac={ac_label} ({ac_conf}), "
            f"blinds={blinds_label} ({blinds_conf})"
        )

        return Prediction(
            ac=ACAction(ac_label),
            blinds=BlindsAction(blinds_label),
            ac_confidence=ac_conf,
            blinds_confidence=blinds_conf,
        )
