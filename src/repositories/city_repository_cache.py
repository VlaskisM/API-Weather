from abc import ABC, abstractmethod
from typing import Any
from src.models.model_city import City
from src.schemas.schemas_city import CityOutPut
from redis import Redis


class AbstractCacheCityRepository:

    @abstractmethod
    async def get_by_name(name_city: str) -> City | None:
        ...

    @abstractmethod
    async def add_city(city: CityOutPut) -> None:
        ...

class CacheCityRepository:

    def __init__(self, session: Any, redis: Redis):
        self._session = session
        self._redis = redis

    async def get_by_name(self, name_city: str) -> City | None:
        name_city_cache = await self._redis.get(name_city)
        if name_city_cache:
            

        


