"""
===============================================================================

    Simulação de gasto energético comparativo.

    Corre 24 horas de leituras sintéticas (3 dias-tipo de Braga: inverno,
    meia-estação, verão) através de três políticas de controlo do AC e
    compara o tempo de atividade resultante e o consumo energético estimado.

    Uso:
        uv run -m pi_server.eval.simulate_day

===============================================================================
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Final

from pi_server.core.comfort_policy import decide
from pi_server.core.domain import DHT11Data, LightSensorData, SensorData
from pi_server.ml.ml_model import MLModel

log = logging.getLogger(__name__)


_AC_POWER_COOL_KW: Final[float] = 1.0
_AC_POWER_HEAT_KW: Final[float] = 1.2

_REACTIVE_COOL_THRESHOLD_C: Final[float] = 23.0
_REACTIVE_HEAT_THRESHOLD_C: Final[float] = 21.0

_LIGHT_THRESHOLD: Final[int] = 500
_HOURS: Final[list[int]] = list(range(24))


# Perfis horários para Braga (PT) inspirados nas normais climatológicas do
# IPMA. Cada tuplo é (temperatura_c, humidade_pct, light_level [0-1023]).
_PROFILE_WINTER: Final[list[tuple[float, float, int]]] = [
    (6, 85, 0),    (5, 85, 0),    (5, 88, 0),    (4, 90, 0),
    (4, 90, 0),    (4, 90, 0),    (4, 88, 0),    (5, 85, 100),
    (6, 80, 300),  (8, 75, 500),  (10, 70, 700), (11, 68, 800),
    (12, 65, 850), (13, 65, 850), (13, 65, 750), (12, 68, 600),
    (11, 72, 400), (10, 75, 200), (9, 80, 50),   (8, 82, 0),
    (8, 83, 0),    (7, 84, 0),    (7, 85, 0),    (6, 85, 0),
]

_PROFILE_MID: Final[list[tuple[float, float, int]]] = [
    (11, 75, 0),    (10, 75, 0),    (10, 78, 0),    (10, 80, 0),
    (9, 80, 0),     (9, 80, 0),     (10, 78, 150),  (11, 75, 400),
    (13, 70, 600),  (15, 65, 800),  (17, 62, 900),  (18, 60, 950),
    (19, 58, 950),  (19, 58, 900),  (18, 60, 800),  (17, 62, 700),
    (16, 65, 500),  (15, 70, 300),  (13, 73, 100),  (12, 75, 20),
    (12, 75, 0),    (11, 75, 0),    (11, 75, 0),    (11, 75, 0),
]

_PROFILE_SUMMER: Final[list[tuple[float, float, int]]] = [
    (21, 65, 0),    (20, 68, 0),    (19, 70, 0),    (19, 70, 0),
    (18, 72, 0),    (18, 72, 100),  (19, 70, 300),  (21, 65, 500),
    (23, 60, 700),  (26, 55, 850),  (28, 50, 950),  (30, 48, 1000),
    (31, 45, 1023), (32, 45, 1023), (32, 47, 1000), (31, 50, 950),
    (30, 55, 850),  (28, 60, 700),  (26, 62, 500),  (24, 65, 300),
    (23, 65, 100),  (22, 65, 20),   (21, 65, 0),    (21, 65, 0),
]


@dataclass(slots=True, frozen=True)
class DayArchetype:
    name: str
    month: int
    profile: list[tuple[float, float, int]]


_ARCHETYPES: Final[list[DayArchetype]] = [
    DayArchetype("Inverno (Jan)", 1, _PROFILE_WINTER),
    DayArchetype("Meia-estação (Abr)", 4, _PROFILE_MID),
    DayArchetype("Verão (Jul)", 7, _PROFILE_SUMMER),
]


def _to_sensor_data(
    temp: float, hum: float, light: int, hour: int, month: int
) -> SensorData:
    ts = datetime(2026, month, 15, hour=hour).timestamp()
    return SensorData(
        dht11=DHT11Data(temperature=temp, humidity=hum),
        light=LightSensorData(light_level=light, is_bright=light >= _LIGHT_THRESHOLD),
        timestamp=ts,
    )


def _simulate_pi_server(model: MLModel, archetype: DayArchetype) -> dict[str, int]:
    counts = {"cool": 0, "heat": 0, "off": 0}
    for hour, (temp, hum, light) in zip(_HOURS, archetype.profile):
        data = _to_sensor_data(temp, hum, light, hour, archetype.month)
        prediction = model.predict(data)
        decision = decide(prediction)
        mode = decision.hvac_mode or "off"
        counts[mode] = counts.get(mode, 0) + 1
    return counts


def _simulate_always_on(_archetype: DayArchetype, mode: str) -> dict[str, int]:
    counts = {"cool": 0, "heat": 0, "off": 0}
    counts[mode] = 24
    return counts


def _simulate_reactive(archetype: DayArchetype) -> dict[str, int]:
    counts = {"cool": 0, "heat": 0, "off": 0}
    for temp, _hum, _light in archetype.profile:
        if temp > _REACTIVE_COOL_THRESHOLD_C:
            counts["cool"] += 1
        elif temp < _REACTIVE_HEAT_THRESHOLD_C:
            counts["heat"] += 1
        else:
            counts["off"] += 1
    return counts


def _to_kwh(counts: dict[str, int]) -> float:
    return (
        counts.get("cool", 0) * _AC_POWER_COOL_KW
        + counts.get("heat", 0) * _AC_POWER_HEAT_KW
    )


def _always_on_mode_for(archetype: DayArchetype) -> str:
    # Utilizador que liga de manhã e esquece. Na meia-estação as manhãs
    # ainda são frias em Braga, pelo que a escolha realista é "heat".
    if "Verão" in archetype.name:
        return "cool"
    return "heat"


def main() -> None:
    logging.basicConfig(level=logging.WARNING)
    model = MLModel(models_dir=Path("assets/models"))

    print("\n" + "=" * 78)
    print("RESULTADOS DA SIMULAÇÃO — gasto energético comparativo")
    print("=" * 78)

    summary_rows: list[tuple[str, float, float, float, float, float]] = []

    for arch in _ARCHETYPES:
        ps = _simulate_pi_server(model, arch)
        ao = _simulate_always_on(arch, _always_on_mode_for(arch))
        rx = _simulate_reactive(arch)

        print(f"\n### {arch.name}\n")
        print("| Política           | cool (h) | heat (h) | off (h) | Energia (kWh/dia) |")
        print("|--------------------|---------:|---------:|--------:|------------------:|")
        for name, c in (("pi_server", ps), ("Sempre ligado", ao), ("Reativo manual", rx)):
            kwh = _to_kwh(c)
            print(
                f"| {name:<18} | {c['cool']:>8} | {c['heat']:>8} | {c['off']:>7} | {kwh:>17.2f} |"
            )

        ps_kwh = _to_kwh(ps)
        ao_kwh = _to_kwh(ao)
        rx_kwh = _to_kwh(rx)
        red_vs_ao = 100.0 * (1.0 - ps_kwh / ao_kwh) if ao_kwh > 0 else 0.0
        red_vs_rx = 100.0 * (1.0 - ps_kwh / rx_kwh) if rx_kwh > 0 else 0.0
        summary_rows.append((arch.name, ps_kwh, ao_kwh, rx_kwh, red_vs_ao, red_vs_rx))

    print("\n### Síntese — kWh/dia e redução face a baselines\n")
    print(
        "| Dia-tipo            | pi_server | Sempre ligado | Reativo manual"
        " | Δ vs. Sempre ligado | Δ vs. Reativo manual |"
    )
    print(
        "|---------------------|----------:|--------------:|---------------:"
        "|--------------------:|---------------------:|"
    )
    for name, ps_k, ao_k, rx_k, rd_ao, rd_rx in summary_rows:
        print(
            f"| {name:<19} | {ps_k:>9.2f} | {ao_k:>13.2f} | {rx_k:>14.2f}"
            f" | {rd_ao:>18.1f} % | {rd_rx:>19.1f} % |"
        )

    total_ps = sum(r[1] for r in summary_rows)
    total_ao = sum(r[2] for r in summary_rows)
    total_rx = sum(r[3] for r in summary_rows)
    print(
        f"\nSoma dos 3 dias-tipo: pi_server = {total_ps:.2f} kWh, "
        f"Sempre ligado = {total_ao:.2f} kWh, Reativo manual = {total_rx:.2f} kWh."
    )
    if total_ao > 0:
        print(f"  Redução acumulada vs. Sempre ligado:   {100*(1-total_ps/total_ao):.1f} %")
    if total_rx > 0:
        print(f"  Redução acumulada vs. Reativo manual:  {100*(1-total_ps/total_rx):.1f} %")
    print()


if __name__ == "__main__":
    main()
