from abc import ABC, abstractmethod
from typing import Callable
from src.clients.weather_client import CityNotFoundError, WeatherClient
from src.models.model_city import City
from src.unit_of_work import UnitOfWork
from src.schemas.schemas_weather import CurrentWeatherOut, WeatherRefreshError, WeatherRefreshOut


class WeatherServiceInterface(ABC):
    @abstractmethod
    async def get_current_weather(self, name_city: str) -> CurrentWeatherOut:
        pass

    @abstractmethod
    async def get_history_weather(self, name_city: str) -> list[CurrentWeatherOut] | None:
        pass

    @abstractmethod
    async def refresh_all_weather(self) -> WeatherRefreshOut:
        pass


class WeatherService(WeatherServiceInterface):
    def __init__(self, uow_factory: Callable[[], UnitOfWork], weather_client: WeatherClient):
        self._uow_factory = uow_factory
        self._weather_client = weather_client


    async def get_current_weather(self, name_city: str) -> CurrentWeatherOut:
        async with self._uow_factory() as uow:
            city = await uow.cities.get_by_name(name_city)
            if city is None:
                raise CityNotFoundError(
                    f"City {name_city} not found in database. Add it via /cities first."
                )

            weather = await uow.weather.get_current_weather_by_coords(self._weather_client, city)
            return CurrentWeatherOut.model_validate(weather.model_dump())



    async def get_history_weather(self, name_city: str) -> list[CurrentWeatherOut] | None:
        async with self._uow_factory() as uow:
            weather = await uow.weather.get_by_name(name_city)
            if weather is None:
                return None
            lst_weather = await uow.weather.get_history_weather(name_city=name_city)

            return [CurrentWeatherOut.model_validate(weather.model_dump()) for weather in lst_weather]

    async def refresh_all_weather(self) -> WeatherRefreshOut:
        cities = await self._load_all_cities()
        errors: list[WeatherRefreshError] = []
        refreshed = 0

        for city in cities:
            try:
                async with self._uow_factory() as uow:
                    await uow.weather.force_refresh_current_weather_by_coords(self._weather_client, city)
                refreshed += 1
            except Exception as exc:
                errors.append(
                    WeatherRefreshError(
                        name_city=city.name_city,
                        reason=str(exc),
                    )
                )

        return WeatherRefreshOut(
            total_cities=len(cities),
            refreshed=refreshed,
            failed=len(errors),
            errors=errors,
        )

    async def _load_all_cities(self) -> list[City]:
        limit = 100
        offset = 0
        cities: list[City] = []

        while True:
            async with self._uow_factory() as uow:
                page = await uow.cities.get_all_citys(limit=limit, offset=offset)
            if not page:
                break
            cities.extend(page)
            offset += limit

        return cities