import logging

from dataclasses import dataclass
from enum import Enum
from typing import Final

from pi_server.core.domain import SensorData

"""
===============================================================================

    Comfort Policy

===============================================================================
"""

log = logging.getLogger(__name__)

_HOT_THRESHOLD:    Final[float] = 26.0
_COLD_THRESHOLD:   Final[float] = 18.0
_BRIGHT_THRESHOLD: Final[int]   = 750
_DARK_THRESHOLD:   Final[int]   = 300


class ThermalComfort(str, Enum):
    HOT = "hot"
    NEUTRAL = "neutral"
    COLD = "cold"


class LuminosityComfort(str, Enum):
    TOO_BRIGHT = "too_bright"
    NEUTRAL = "neutral"
    TOO_DARK = "too_dark"


@dataclass(slots=True, frozen=True)
class ActionDecision:
    hvac_mode: str | None  # "off" | "cool" | "heat" | None (no-op)
    cover_op: str | None   # "open_cover" | "close_cover" | None (keep)


def classify_thermal(data: SensorData) -> ThermalComfort:
    temperature = data.dht11.temperature
    if temperature > _HOT_THRESHOLD:
        return ThermalComfort.HOT
    if temperature < _COLD_THRESHOLD:
        return ThermalComfort.COLD
    return ThermalComfort.NEUTRAL


def classify_luminosity(data: SensorData) -> LuminosityComfort:
    light_level = data.light.light_level
    if light_level > _BRIGHT_THRESHOLD:
        return LuminosityComfort.TOO_BRIGHT
    if light_level < _DARK_THRESHOLD:
        return LuminosityComfort.TOO_DARK
    return LuminosityComfort.NEUTRAL


# Conflict cells avoid working against the thermal goal:
#   HOT  + TOO_DARK   -> don't raise (sun adds heat).
#   COLD + TOO_BRIGHT -> don't lower (sun is free heat).
#   COLD + TOO_DARK   -> raise (sun = light + heat, synergy).
_POLICY: Final[dict[tuple[ThermalComfort, LuminosityComfort], ActionDecision]] = {
    (ThermalComfort.NEUTRAL, LuminosityComfort.NEUTRAL):    ActionDecision("off",  None),
    (ThermalComfort.NEUTRAL, LuminosityComfort.TOO_BRIGHT): ActionDecision("off",  "open_cover"),
    (ThermalComfort.NEUTRAL, LuminosityComfort.TOO_DARK):   ActionDecision("off",  "close_cover"),

    (ThermalComfort.HOT,     LuminosityComfort.NEUTRAL):    ActionDecision("cool", None),
    (ThermalComfort.HOT,     LuminosityComfort.TOO_BRIGHT): ActionDecision("cool", "open_cover"),
    (ThermalComfort.HOT,     LuminosityComfort.TOO_DARK):   ActionDecision("cool", None),

    (ThermalComfort.COLD,    LuminosityComfort.NEUTRAL):    ActionDecision("heat", None),
    (ThermalComfort.COLD,    LuminosityComfort.TOO_BRIGHT): ActionDecision("heat", None),
    (ThermalComfort.COLD,    LuminosityComfort.TOO_DARK):   ActionDecision("heat", "close_cover"),
}


def decide(data: SensorData) -> ActionDecision:
    thermal = classify_thermal(data)
    luminosity = classify_luminosity(data)
    decision = _POLICY[(thermal, luminosity)]
    log.debug(
        f"comfort: thermal={thermal.value}, luminosity={luminosity.value} "
        f"-> hvac_mode={decision.hvac_mode}, cover_op={decision.cover_op}"
    )
    return decision
