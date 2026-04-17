from abc import ABC, abstractmethod
from typing import Any
from src.models.model_city import City
from src.schemas.schemas_city import CityOutPut
from redis.asyncio import Redis
from src.repositories.city_repository import CityRepository


class AbstractCacheCityRepository(ABC):

    @abstractmethod
    async def get_by_name(self, name_city: str) -> City | None:
        ...

    @abstractmethod
    async def add_city(self, city: CityOutPut) -> None:
        ...

    @abstractmethod
    async def get_all_citys(self, limit: int, offset: int) -> list[City]:
        ...

class CacheCityRepository:

    def __init__(self, session: Any, redis: Redis, rep: CityRepository):
        self._session = session
        self._redis = redis
        self._rep = rep

    async def get_by_name(self, name_city: str) -> City | None:
        key = self.get_key(name_city)
        name_city_cache = await self._redis.get(key)
        if name_city_cache is not None:
            return City.model_validate_json(name_city_cache)

        city = await self._rep.get_by_name(name_city=name_city, _session=self._session)

        if city is not None:
            await self._redis.set(key, city.model_dump_json(), ex=3600)

        return city


    async def add_city(self, city: CityOutPut) -> None:
        await self._rep.add_city(city=city, _session=self._session)
        key = self.get_key(city.name_city)
        await self._redis.set(key, city.model_dump_json(), ex=3600)

    async def get_all_citys(self, limit: int, offset: int) -> list[City]:
        return await self._rep.get_all_citys(_session=self._session, limit=limit, offset=offset)


    @staticmethod
    def get_key(name_city: str) -> str:
        return f"cache:city:{name_city.strip().lower()}"

            

        


