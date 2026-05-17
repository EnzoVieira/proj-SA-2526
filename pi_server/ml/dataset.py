"""
===============================================================================

    Synthetic dataset generator

    Produz amostras (temperature, humidity, light_level) com labels para
    BlindsAction e ACAction derivadas de regras heurísticas + ruído.
    Usado para treinar os classificadores na ausência de dados reais
    anotados.

===============================================================================
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from pi_server.core.domain import ACAction, BlindsAction

# Limites físicos plausíveis dos sensores
_TEMP_MIN, _TEMP_MAX = 5.0, 40.0
_HUMIDITY_MIN, _HUMIDITY_MAX = 20.0, 95.0
_LIGHT_MIN, _LIGHT_MAX = 0, 1023

# Limiares das regras heurísticas
_COOL_THRESHOLD = 26.0
_HEAT_THRESHOLD = 18.0
_DARK_THRESHOLD = 300
_BRIGHT_THRESHOLD = 750

# Ruído
_LABEL_FLIP_PROB = 0.05  # 5% das labels trocadas aleatoriamente
_FEATURE_NOISE_STD = {
    "temperature": 0.5,
    "humidity": 2.0,
    "light_level": 25.0,
}


def _label_ac(temp: float) -> ACAction:
    if temp > _COOL_THRESHOLD:
        return ACAction.COOL
    if temp < _HEAT_THRESHOLD:
        return ACAction.HEAT
    return ACAction.OFF


def _label_blinds(light: int, temp: float) -> BlindsAction:
    # Excesso de sol com calor → baixar para reduzir carga térmica
    if light > _BRIGHT_THRESHOLD and temp > _COOL_THRESHOLD:
        return BlindsAction.LOWER
    # Pouca luz → subir para deixar entrar luz natural
    if light < _DARK_THRESHOLD:
        return BlindsAction.RAISE
    # Muito brilho mas temperatura amena → baixar para conforto visual
    if light > _BRIGHT_THRESHOLD:
        return BlindsAction.LOWER
    return BlindsAction.KEEP


def _add_label_noise(
    labels: np.ndarray, classes: list[str], rng: np.random.Generator
) -> np.ndarray:
    mask = rng.random(len(labels)) < _LABEL_FLIP_PROB
    if not mask.any():
        return labels
    noisy = labels.copy()
    for i in np.flatnonzero(mask):
        alternatives = [c for c in classes if c != labels[i]]
        noisy[i] = rng.choice(alternatives)
    return noisy


def generate(n_samples: int = 8000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    # Distribuições mistas: cobrir todos os regimes (frio, ameno, quente)
    temp = np.concatenate([
        rng.normal(15.0, 3.0, n_samples // 3),   # regime frio
        rng.normal(22.0, 2.5, n_samples // 3),   # regime ameno
        rng.normal(29.0, 3.0, n_samples - 2 * (n_samples // 3)),  # quente
    ])
    rng.shuffle(temp)

    humidity = rng.normal(55.0, 15.0, n_samples)
    light = rng.integers(_LIGHT_MIN, _LIGHT_MAX + 1, n_samples).astype(float)

    # Ruído extra nas features para evitar regras perfeitas
    temp += rng.normal(0.0, _FEATURE_NOISE_STD["temperature"], n_samples)
    humidity += rng.normal(0.0, _FEATURE_NOISE_STD["humidity"], n_samples)
    light += rng.normal(0.0, _FEATURE_NOISE_STD["light_level"], n_samples)

    # Recortar para gamas físicas
    temp = np.clip(temp, _TEMP_MIN, _TEMP_MAX)
    humidity = np.clip(humidity, _HUMIDITY_MIN, _HUMIDITY_MAX)
    light = np.clip(light, _LIGHT_MIN, _LIGHT_MAX).astype(int)

    ac_labels = np.array([_label_ac(t).value for t in temp])
    blinds_labels = np.array([_label_blinds(l, t).value for l, t in zip(light, temp)])

    ac_labels = _add_label_noise(ac_labels, [a.value for a in ACAction], rng)
    blinds_labels = _add_label_noise(
        blinds_labels, [b.value for b in BlindsAction], rng
    )

    return pd.DataFrame({
        "temperature": np.round(temp, 2),
        "humidity": np.round(humidity, 2),
        "light_level": light,
        "ac_action": ac_labels,
        "blinds_action": blinds_labels,
    })


def main():
    parser = argparse.ArgumentParser(description="Gera dataset sintético.")
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
    print("\nAC label distribution:")
    print(df["ac_action"].value_counts())
    print("\nBlinds label distribution:")
    print(df["blinds_action"].value_counts())


if __name__ == "__main__":
    main()
