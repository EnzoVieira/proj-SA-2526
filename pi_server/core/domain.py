from enum import Enum

from pydantic import BaseModel

"""
===============================================================================

    Domain	

===============================================================================
"""


# TODO: update this according to target, and sensor data according to what will be sent by the arduino sensors
class ConditionLabel(str, Enum):
    COLD = "cold"
    HOT = "hot"
    NORMAL = "normal"
    DRY = "dry"
    HUMID = "humid"
    ...


class SensorData(BaseModel):
    temperature: float
    humidity: float
    co2: float
