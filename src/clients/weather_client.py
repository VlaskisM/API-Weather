from httpx import AsyncClient, TimeoutException, RequestError, HTTPStatusError
from src.config import settings
from abc import ABC, abstractmethod
from typing import Any



class CityNotFoundError(Exception):
    ...

class WeatherApiTimeoutError(Exception):
    ...

class ServerErrorOWM(Exception):
    ...


class WeatherClientInterface(ABC):
    
    @abstractmethod
    async def geocode(self, name_city: str) -> tuple[float, float]:
        pass


    @abstractmethod
    async def get_current_weather_by_coords(
        self,
        *,
        name_city: str,
        latitude: float,
        longitude: float,
    ) -> dict[str, Any]:
        pass


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




    async def get_current_weather_by_coords(
        self,
        *,
        name_city: str,
        latitude: float,
        longitude: float,
    ) -> dict[str, Any]:
        appid = settings.OWM_API_KEY
        weather_url = settings.OWM_WEATHER_URL

        params = {
            "lat": latitude,
            "lon": longitude,
            "appid": appid,
            "units": "metric",
        }

        try:
            async with AsyncClient(timeout=10) as client:
                resp = await client.get(weather_url, params=params)
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

        weather_items = data.get("weather") or []
        weather_main = weather_items[0] if weather_items else {}
        main_data = data.get("main") or {}
        wind_data = data.get("wind") or {}

        return {
            "name_city": name_city,
            "temperature": float(main_data.get("temp", 0.0)),
            "feels_like": float(main_data.get("feels_like", 0.0)),
            "humidity": int(main_data.get("humidity", 0)),
            "description": weather_main.get("description", ""),
            "wind_speed": float(wind_data.get("speed", 0.0)),
        }

