from httpx import AsyncClient
from src.config import settings
from abc import ABC, abstractmethod



class CityNotFoundError(Exception):
    ...

class WeatherClientInterface(ABC):
    
    @abstractmethod
    async def geocode(self, name_city: str) -> tuple[float, float]:
        ...


class WeatherClient(WeatherClientInterface):

    async def geocode(self, name_city: str) -> tuple[float, float]:
        
        url = settings.OWM_URL

        params = {
            "q" : name_city,
            "limit" : 1,
            "appid" : url
        }
        
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        if not data:
            raise CityNotFoundError(f"City {name_city} not found")

        return tuple(data[0].get("lat"), data[0].get("lon"))

