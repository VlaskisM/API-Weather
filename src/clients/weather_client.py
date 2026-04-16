from httpx import AsyncClient, TimeoutException, RequestError, HTTPStatusError
from src.config import settings
from abc import ABC, abstractmethod



class CityNotFoundError(Exception):
    ...

class WeatherApiTimeoutError(Exception):
    ...

class ServerErrorOWM(Exception):
    ...


class WeatherClientInterface(ABC):
    
    @abstractmethod
    async def geocode(self, name_city: str) -> tuple[float, float]:
        ...


class WeatherClient(WeatherClientInterface):

    async def geocode(self, name_city: str) -> tuple[float, float]:
        
        appid = settings.OWM_API_KEY

        params = {
            "q" : name_city,
            "limit" : 1,
            "appid" : appid
        }
        

        try:
            async with AsyncClient(timeout=10) as client:
                resp = await client.get(settings.OWM_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
        except TimeoutException as e:
            raise WeatherApiTimeoutError("OWM timeout") from e
        except HTTPStatusError as e:
            status = e.response.status_code
            raise ServerErrorOWM(f"OWM HTTP error: {status}") from e
        except RequestError as e:
            raise RuntimeError("OWM network error") from e
        

        if not data:
            raise CityNotFoundError(f"City {name_city} not found")

        return tuple([data[0].get("lat"), data[0].get("lon")])

