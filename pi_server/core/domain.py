from enum import Enum

from pydantic import BaseModel

"""
===============================================================================

    Domain

===============================================================================
"""


class ThermalComfort(str, Enum):
    HOT = "hot"
    NEUTRAL = "neutral"
    COLD = "cold"


class LuminosityComfort(str, Enum):
    TOO_BRIGHT = "too_bright"
    NEUTRAL = "neutral"
    TOO_DARK = "too_dark"


class DHT11Data(BaseModel):
    """Dados do sensor DHT11 (temperatura e humidade)"""
    temperature: float  # Celsius
    humidity: float     # Percentagem (%)


class LightSensorData(BaseModel):
    """Dados do sensor de luz analógico"""
    light_level: int    # 0-1023 (valor analógico)
    is_bright: bool     # True se light_level >= threshold


class SensorData(BaseModel):
    """Agregação de todos os dados de sensores"""
    dht11: DHT11Data
    light: LightSensorData
    timestamp: float | None = None


class Prediction(BaseModel):
    """Labels de conforto previstas pelo modelo ML"""
    thermal: ThermalComfort
    luminosity: LuminosityComfort
    thermal_confidence: float | None = None
    luminosity_confidence: float | None = None
