from abc import ABC, abstractmethod
from src.unit_of_work import UnitOfWork
from src.schemas.schemas_city import CityOutPut
from typing import Callable
from src.clients.weather_client import WeatherClient
from src.models.model_city import City

class CityServiceInterface(ABC):

    @abstractmethod
    async def add_city(self, name_city: str) -> CityOutPut | None:
        pass

    @abstractmethod
    async def get_all_citys(self) -> list[CityOutPut]:
        pass

    @abstractmethod
    async def get_all_citys(self, limit: int, offset: int) -> list[CityOutPut]:
        pass

    @abstractmethod
    async def del_city(self, name_city: str) -> CityOutPut:
        pass

class CityService(CityServiceInterface):

    def __init__(self, uow_factory: Callable[[], UnitOfWork], weather_client: WeatherClient):
        self._uow_factory = uow_factory
        self._weather_client = weather_client

    async def add_city(self, name_city: str) -> CityOutPut | None:
        async with self._uow_factory() as uow:
            city = await uow.cities.get_by_name(name_city)
            if city:
                return None
            
            city = await self._create_city_output(
                name_city=name_city,
                uow=uow
            )
            return city

    
    async def _create_city_output(self, name_city: str, uow: UnitOfWork) -> CityOutPut:
        latitude, longitude = await self._weather_client.geocode(name_city=name_city)
        city = CityOutPut(
            name_city=name_city,
            latitude=latitude,
            longitude=longitude,
        )
        await uow.cities.add_city(city)
        return city

    async def get_all_citys(self, limit: int, offset: int) -> list[CityOutPut]:
        async with self._uow_factory() as uow:
            cities = await uow.cities.get_all_citys(limit=limit, offset=offset)
            return [self._to_city_output(city) for city in cities]


    async def del_city(self, name_city) -> CityOutPut:
        async with self._uow_factory() as uow:
            city = await uow.cities.get_by_name(name_city)
            if not city:
                return None

            city = await uow.cities.del_city(name_city)

            return self._to_city_output(city)


    @staticmethod
    def _to_city_output(city: City) -> CityOutPut:
        return CityOutPut(
            name_city=city.name_city,
            latitude=city.latitude,
            longitude=city.longitude,
        )
    
                            
        
        

