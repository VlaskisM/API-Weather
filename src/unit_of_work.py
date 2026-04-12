from abc import ABC, abstractmethod


class UnitOfWorkInterface(ABC):
    repository : AbstractCityRepository

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
