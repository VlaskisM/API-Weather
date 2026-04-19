from abc import ABC, abstractmethod
from typing import Any

from src.schemas.schemas_weather import CurrentWeatherOut


class AbstractWeatherRepository(ABC):
    @abstractmethod
    async def get_current_weather(self, name_city: str, _session: Any) -> CurrentWeatherOut | None:
        pass

    @abstractmethod
    async def save_current_weather(self, weather: CurrentWeatherOut, _session: Any) -> None:
        pass

    @abstractmethod
    async def delete_current_weather(self, name_city: str, _session: Any) -> None:
        pass


class WeatherRepository:
    async def get_current_weather(
        self,
        name_city: str,
        _session: Any,
    ) -> CurrentWeatherOut | None:
        # Storage integration will be implemented with weather collection model.
        return None

    async def save_current_weather(
        self,
        weather: CurrentWeatherOut,
        _session: Any,
    ) -> None:
        # Storage integration will be implemented with weather collection model.
        return None

    async def delete_current_weather(
        self,
        name_city: str,
        _session: Any,
    ) -> None:
        # Storage integration will be implemented with weather collection model.
        return None
