import logging

from dataclasses import dataclass

from pi_server.core.domain import ConditionLabel, SensorData

"""
===============================================================================

	ML Model

===============================================================================
"""

log = logging.getLogger(__name__)


# TODO: load model here later
@dataclass(slots=True)
class MLModel:
    def __init__(self):
        pass

    def predict(self, data: SensorData) -> ConditionLabel:
        log.info(f"Predicting: {data}...")
        pass
