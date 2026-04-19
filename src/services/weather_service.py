from abc import ABC, abstractmethod
from typing import Any, Callable

from src.clients.weather_client import CityNotFoundError, WeatherClient
from src.unit_of_work import UnitOfWork


class WeatherServiceInterface(ABC):
    @abstractmethod
    async def get_current_weather(self, name_city: str) -> dict[str, Any]:
        ...


class WeatherService(WeatherServiceInterface):
    def __init__(self, uow_factory: Callable[[], UnitOfWork], weather_client: WeatherClient):
        self._uow_factory = uow_factory
        self._weather_client = weather_client

    async def get_current_weather(self, name_city: str) -> dict[str, Any]:
        async with self._uow_factory() as uow:
            city = await uow.cities.get_by_name(name_city)
            if city is None:
                raise CityNotFoundError(
                    f"City {name_city} not found in database. Add it via /cities first."
                )
                
            return await self._weather_client.get_current_weather_by_coords(
                name_city=city.name_city,
                latitude=city.latitude,
                longitude=city.longitude,
            )
