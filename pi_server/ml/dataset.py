"""
===============================================================================

    Synthetic dataset generator

    Produz amostras (temperature, humidity, light_level, hour_of_day) com
    labels de conforto (thermal_comfort, luminosity_comfort) amostradas
    estocasticamente a partir de sigmoides. Soft labels: codificam interacção
    humidade↔temp (heat-index) e hora-do-dia↔luz (tolerância noturna), pelo
    que o RF aprende padrões que um if/else não consegue exprimir.

===============================================================================
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from pi_server.core.domain import LuminosityComfort, ThermalComfort

# Limites físicos plausíveis dos sensores
_TEMP_MIN, _TEMP_MAX = 5.0, 40.0
_HUMIDITY_MIN, _HUMIDITY_MAX = 20.0, 95.0
_LIGHT_MIN, _LIGHT_MAX = 0, 1023

# Ruído nas features (evita regras perfeitas)
_FEATURE_NOISE_STD = {
    "temperature": 0.5,
    "humidity": 2.0,
    "light_level": 25.0,
}

# Parâmetros da labelling (sigmoides)
_COLD_THRESHOLD = 18.0
_HOT_BASE_THRESHOLD = 26.0
_DAY_START, _DAY_END = 7, 20  # [start, end) — horas locais (Portugal verão)
_BRIGHT_DAY = 800.0
_DARK_DAY = 300.0
_BRIGHT_NIGHT = 200.0


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def _thermal_probs(temp: np.ndarray, humidity: np.ndarray) -> np.ndarray:
    # Hot threshold cai 1°C por cada +20% de humidade acima de 50% (heat-index intuition).
    hot_threshold = _HOT_BASE_THRESHOLD - np.maximum(0.0, (humidity - 50.0)) / 20.0
    p_hot = _sigmoid((temp - hot_threshold) * 1.0)
    p_cold = _sigmoid((_COLD_THRESHOLD - temp) * 1.0)
    p_neutral = np.maximum(0.0, 1.0 - p_hot - p_cold)
    stacked = np.stack([p_hot, p_neutral, p_cold], axis=1)
    stacked /= stacked.sum(axis=1, keepdims=True)
    return stacked  # colunas: HOT, NEUTRAL, COLD


def _luminosity_probs(light: np.ndarray, hour: np.ndarray) -> np.ndarray:
    is_day = (hour >= _DAY_START) & (hour < _DAY_END)
    p_bright = np.where(
        is_day,
        _sigmoid((light - _BRIGHT_DAY) / 50.0),
        _sigmoid((light - _BRIGHT_NIGHT) / 40.0),
    )
    p_dark = np.where(
        is_day,
        _sigmoid((_DARK_DAY - light) / 30.0),
        0.0,
    )
    p_neutral = np.maximum(0.0, 1.0 - p_bright - p_dark)
    stacked = np.stack([p_bright, p_neutral, p_dark], axis=1)
    stacked /= stacked.sum(axis=1, keepdims=True)
    return stacked  # colunas: TOO_BRIGHT, NEUTRAL, TOO_DARK


def _sample_labels(
    probs: np.ndarray, classes: list[str], rng: np.random.Generator
) -> np.ndarray:
    # Amostragem categórica vectorizada via inverse-CDF nas probs cumulativas.
    u = rng.random(len(probs))
    cum = np.cumsum(probs, axis=1)
    idx = (u[:, None] < cum).argmax(axis=1)
    return np.array(classes)[idx]


def generate(n_samples: int = 8000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    # Distribuições mistas para cobrir todos os regimes (frio, ameno, quente).
    temp = np.concatenate([
        rng.normal(15.0, 3.0, n_samples // 3),
        rng.normal(22.0, 2.5, n_samples // 3),
        rng.normal(29.0, 3.0, n_samples - 2 * (n_samples // 3)),
    ])
    rng.shuffle(temp)

    humidity = rng.normal(55.0, 15.0, n_samples)
    light = rng.integers(_LIGHT_MIN, _LIGHT_MAX + 1, n_samples).astype(float)
    hour = rng.integers(0, 24, n_samples)

    temp += rng.normal(0.0, _FEATURE_NOISE_STD["temperature"], n_samples)
    humidity += rng.normal(0.0, _FEATURE_NOISE_STD["humidity"], n_samples)
    light += rng.normal(0.0, _FEATURE_NOISE_STD["light_level"], n_samples)

    temp = np.clip(temp, _TEMP_MIN, _TEMP_MAX)
    humidity = np.clip(humidity, _HUMIDITY_MIN, _HUMIDITY_MAX)
    light = np.clip(light, _LIGHT_MIN, _LIGHT_MAX).astype(int)

    thermal_probs = _thermal_probs(temp, humidity)
    luminosity_probs = _luminosity_probs(light.astype(float), hour)

    thermal_classes = [
        ThermalComfort.HOT.value,
        ThermalComfort.NEUTRAL.value,
        ThermalComfort.COLD.value,
    ]
    luminosity_classes = [
        LuminosityComfort.TOO_BRIGHT.value,
        LuminosityComfort.NEUTRAL.value,
        LuminosityComfort.TOO_DARK.value,
    ]

    thermal_labels = _sample_labels(thermal_probs, thermal_classes, rng)
    luminosity_labels = _sample_labels(luminosity_probs, luminosity_classes, rng)

    return pd.DataFrame({
        "temperature": np.round(temp, 2),
        "humidity": np.round(humidity, 2),
        "light_level": light,
        "hour_of_day": hour.astype(int),
        "thermal_comfort": thermal_labels,
        "luminosity_comfort": luminosity_labels,
    })


def main():
    parser = argparse.ArgumentParser(description="Gera dataset sintético de conforto.")
    parser.add_argument("--n", type=int, default=8000, help="Número de amostras.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("assets/dataset.csv"),
        help="Caminho de saída (CSV).",
    )
    args = parser.parse_args()

    df = generate(n_samples=args.n, seed=args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)

    print(f"Wrote {len(df)} samples to {args.out}")
    print("\nThermal comfort distribution:")
    print(df["thermal_comfort"].value_counts())
    print("\nLuminosity comfort distribution:")
    print(df["luminosity_comfort"].value_counts())


if __name__ == "__main__":
    main()
