from abc import ABC, abstractmethod
from typing import Any
from src.repositories.city_repository_cache import AbstractCacheCityRepository, CacheCityRepository
from src.repositories.city_repository import CityRepository
from src.repositories.weather_repository import WeatherRepository
from src.repositories.weather_repository_cache import AbstractCacheWeatherRepository, CacheWeatherRepository
from redis import Redis

class UnitOfWorkInterface(ABC):
    cities: AbstractCacheCityRepository
    weather: AbstractCacheWeatherRepository

    @abstractmethod
    async def __aenter__(self):
        ...

    @abstractmethod
    async def __aexit__(self, *args):
        ...

    @abstractmethod
    async def commit(self):
        ...

    @abstractmethod
    async def rollback(self):
        ...


class UnitOfWork(UnitOfWorkInterface):

    def __init__(
        self,
        client: Any,
        redis: Redis,
        rep: CityRepository,
        weather_rep: WeatherRepository,
    ):
        self._client = client
        self._redis = redis
        self._city_rep = rep
        self._session: Any | None = None
        self.cities: AbstractCacheCityRepository
        self.weather: AbstractCacheWeatherRepository
        self._weather_rep = weather_rep
        

    async def __aenter__(self):
        # Transactions are disabled: repositories run without Mongo session.
        self._session = None
        self.cities = CacheCityRepository(session=self._session, redis=self._redis, rep=self._city_rep)
        self.weather = CacheWeatherRepository(session=self._session, redis=self._redis, rep=self._weather_rep)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._session = None
            

    async def commit(self):
        return None

    async def rollback(self):
        return None
