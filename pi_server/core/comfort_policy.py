import logging

from dataclasses import dataclass
from typing import Final

from pi_server.core.domain import (
    LuminosityComfort,
    Prediction,
    ThermalComfort,
)

"""
===============================================================================

    Comfort Policy

===============================================================================
"""

log = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class ActionDecision:
    hvac_mode: str | None  # "off" | "cool" | "heat" | None (no-op)
    cover_op: str | None   # "open_cover" | "close_cover" | None (keep)


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


def decide(prediction: Prediction) -> ActionDecision:
    decision = _POLICY[(prediction.thermal, prediction.luminosity)]
    log.debug(
        f"comfort: thermal={prediction.thermal.value}, luminosity={prediction.luminosity.value} "
        f"-> hvac_mode={decision.hvac_mode}, cover_op={decision.cover_op}"
    )
    return decision
