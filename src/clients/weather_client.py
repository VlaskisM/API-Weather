from httpx import AsyncClient
from src.config import settings
from abc import ABC, abstractmethod

class WeatherClientInterface(ABC):
    
    @abstractmethod
    async def geocode(self, name_city: str) -> tuple[float, float]:
        ...


class WeatherClient(WeatherClientInterface):


