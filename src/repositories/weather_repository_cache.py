from abc import ABC, abstractmethod
from typing import Any

from redis.asyncio import Redis

from src.repositories.weather_repository import WeatherRepository
from src.schemas.schemas_weather import CurrentWeatherOut


class AbstractCacheWeatherRepository(ABC):
    @abstractmethod
    async def get_current_weather(self, name_city: str) -> CurrentWeatherOut | None:
        pass

    @abstractmethod
    async def save_current_weather(self, weather: CurrentWeatherOut) -> None:
        pass

    @abstractmethod
    async def delete_current_weather(self, name_city: str) -> None:
        pass


class CacheWeatherRepository:
    def __init__(self, session: Any, redis: Redis, rep: WeatherRepository):
        self._session = session
        self._redis = redis
        self._rep = rep

    async def get_current_weather(self, name_city: str) -> CurrentWeatherOut | None:
        key = self.get_key(name_city)
        weather_cache = await self._redis.get(key)
        if weather_cache is not None:
            return CurrentWeatherOut.model_validate_json(weather_cache)

        weather = await self._rep.get_current_weather(name_city=name_city, _session=self._session)
        if weather is not None:
            await self._redis.set(key, weather.model_dump_json(), ex=900)
        return weather

    async def save_current_weather(self, weather: CurrentWeatherOut) -> None:
        await self._rep.save_current_weather(weather=weather, _session=self._session)
        await self._redis.set(self.get_key(weather.name_city), weather.model_dump_json(), ex=900)

    async def delete_current_weather(self, name_city: str) -> None:
        await self._redis.delete(self.get_key(name_city))
        await self._rep.delete_current_weather(name_city=name_city, _session=self._session)

    @staticmethod
    def get_key(name_city: str) -> str:
        return f"cache:weather:current:{name_city.strip().lower()}"
