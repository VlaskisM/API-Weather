from abc import ABC, abstractmethod
from typing import Any
from redis.asyncio import Redis
from src.repositories.weather_repository import WeatherRepository
from src.models.model_weather import Weather
from src.models.model_city import City
from src.clients.weather_client import WeatherClient



class AbstractCacheWeatherRepository(ABC):

    @abstractmethod
    async def get_by_name(self, name_city: str) -> Weather | None:
        pass

    @abstractmethod
    async def get_current_weather_by_coords(self, weather_client: WeatherClient, city: City) -> Weather:
        pass

    @abstractmethod
    async def force_refresh_current_weather_by_coords(self, weather_client: WeatherClient, city: City) -> Weather:
        pass

    @abstractmethod
    async def get_history_weather(self, name_city: str) -> list[Weather]:
        pass

    @abstractmethod
    async def delete_by_city(self, name_city: str) -> int:
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

        payload = await weather_client.get_current_weather_by_coords(
            name_city=city.name_city,
            latitude=city.latitude,
            longitude=city.longitude,
        )
        weather = Weather.model_validate(payload)
        await self._redis.set(key, weather.model_dump_json())
        await self._rep.add_weather(weather, session=self._session)
        return weather


    async def force_refresh_current_weather_by_coords(self, weather_client: WeatherClient, city: City) -> Weather:
        key = self.get_key(city.name_city)
        payload = await weather_client.get_current_weather_by_coords(
            name_city=city.name_city,
            latitude=city.latitude,
            longitude=city.longitude,
        )
        weather = Weather.model_validate(payload)
        await self._redis.set(key, weather.model_dump_json())
        await self._rep.add_weather(weather, session=self._session)
        return weather


    async def get_by_name(self, name_city: str) -> Weather | None:
    
        key = self.get_key(name_city)
        cached_weather = await self._redis.get(key)
        if cached_weather is not None:
            return Weather.model_validate_json(cached_weather)

        weather = await self._rep.get_by_name(
            name_city=name_city,
            session=self._session,
        )
        return weather


    async def get_history_weather(self, name_city: str) -> list[Weather]:
        return await self._rep.get_history_weather(name_city=name_city, session=self._session)

    async def delete_by_city(self, name_city: str) -> int:
        key = self.get_key(name_city)
        await self._redis.delete(key)
        return await self._rep.delete_history_by_name(name_city=name_city, session=self._session)


    @staticmethod
    def get_key(name_city: str) -> str:
        return f"cache:weather:{name_city.strip().lower()}"