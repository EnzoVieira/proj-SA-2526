from enum import Enum

from pydantic import BaseModel

"""
===============================================================================

    Domain	

===============================================================================
"""

class ConditionLabel(str, Enum):
    COLD = "cold"
    HOT = "hot"
    NORMAL = "normal"
    DARK = "dark"
    BRIGHT = "bright"


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
