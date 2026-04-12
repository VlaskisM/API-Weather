from abc import ABC, abstractmethod
from src.uow import UnitOfWork
from src.schemas.schemas_city import CityOutPut
from src.clients.weather_client import WeatherClient

class CityServiceInterface(ABC):

    @abstractmethod
    async def add_city(self, name_city: str) -> CityOutPut | None:
        pass

class CityService(CityServiceInterface):

    def __init__(self, uow_factory: UnitOfWork, weather_client: WeatherClient):
        self._uow_factory = uow_factory()
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
            await uow.commit()
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
    
                            
        
        

