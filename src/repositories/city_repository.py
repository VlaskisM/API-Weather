from abc import ABC, abstractmethod
from typing import Any  
from src.models.model_city import City
from src.schemas.schemas_city import CityOutPut

class AbstractCityRepository(ABC):

    @abstractmethod
    async def get_by_name(name_city: str, _session: Any) -> City | None:
        ...

    @abstractmethod
    async def add_city(city: CityOutPut, _session: Any) -> None:
        ...

    
class CityRepository:

    async def add_city(self, city: CityOutPut, _session: Any) -> None:
        city_odm = City(name_city=city.name_city, latitude=city.latitude, longitude=city.longitude)
        await city_odm.insert(session=_session)

    async def get_by_name(self, name_city: str, _session: Any) -> City | None:
        return await City.find_one(City.name_city == name_city, session=_session)





