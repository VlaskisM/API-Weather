from abc import ABC, abstractmethod
from typing import Any
from redis.asyncio import Redis
from src.repositories.weather_repository import WeatherRepository
from src.models.model_weather import Weather
from src.models.model_city import City
from src.clients.weather_client import WeatherClient


class AbstractCacheWeatherRepository(ABC):
    @abstractmethod
    async def get_current_weather_by_coords(self, weather_client: WeatherClient, city: City) -> Weather:
        pass


class CacheWeatherRepository:
    def __init__(self, session: Any, redis: Redis, rep: WeatherRepository):
        self._session = session
        self._redis = redis
        self._rep = rep


    async def get_current_weather_by_coords(self, weather_client: WeatherClient, city: City) -> Weather:
        key = self.get_key(city.name_city)
        weather_cache = await self._redis.get(key)
        if weather_cache is not None:
            return Weather.model_validate_json(weather_cache)

        weather_cache = await weather_client.get_current_weather_by_coords(
            name_city=city.name_city,
            latitude=city.latitude,
            longitude=city.longitude
        )

        await self._redis.set(key, weather_cache.model_dump_json())
        await self._rep.add_weather(Weather.model_validate(weather_cache), session = self._session)


        return Weather.model_validate(weather_cache)

    @staticmethod
    def get_key(name_city: str) -> str:
        return f"cache:weather:current:{name_city.strip().lower()}"
