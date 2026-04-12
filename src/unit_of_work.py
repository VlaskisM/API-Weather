from abc import ABC, abstractmethod
from pymongo_asyncio import AsyncMongoClient
from pymongo import ClientSession
from src.repositories.city_repository import AbstractCityRepository, CityRepository

class UnitOfWorkInterface(ABC):
    cities : AbstractCityRepository

    @abstractmethod
    async def __aenter__(self):
        ...

    @abstractmethod
    async def __aexit__(self, *args):
        self.rollback()

    @abstractmethod
    async def commit(self):
        ...

    @abstractmethod
    async def rollback(self):
        ...


class UnitOfWork(UnitOfWorkInterface):

    def __init__(self, client):
        self._client = client
        self._session: ClientSession | None = None
        self._transaction = None
        self.cities: AbstractCityRepository


    async def __aenter__(self):
        self._session = await self._client.start_session() # Тут возвращается контекстный менеджер
        self._transaction = self._session.start_transaction()
        await self._transaction.__aenter__()
        self.cities = CityRepository(session = self._session)
        return self

    async def __aexit__(self, *args):
        ...

    async def commit(self):
        return await super().commit()

    async def rollback(self):
        return await super().rollback()
