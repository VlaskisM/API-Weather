from abc import ABC, abstractmethod
from typing import Any
from src.repositories.city_repository_cache import AbstractCacheCityRepository, CacheCityRepository
from src.db.db_redis import redis

class UnitOfWorkInterface(ABC):
    cities : AbstractCacheCityRepository

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
        self._session: Any | None = None
        self.cities: AbstractCacheCityRepository


    async def __aenter__(self):
        self._session = self._client.start_session() # Тут возвращается контекстный менеджер
        self._transaction = await self._session.start_transaction()
        self.cities = CacheCityRepository(session = self._session, redis = redis)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        else:
            await self.commit()
        
        if self._session is not None:
            self._session.end_session()

    async def commit(self):
        await self._session.commit_transaction()

    async def rollback(self):
        await self._session.abort_transaction()
