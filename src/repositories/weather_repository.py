from abc import ABC, abstractmethod
from typing import Any
from src.schemas.schemas_weather import CurrentWeatherOut
from src.models.model_weather import Weather


class AbstractWeatherRepository(ABC):
    
    @abstractmethod
    async def add_weather(weather: Weather) -> None:
        pass
    

class WeatherRepository(AbstractWeatherRepository):
    

    async def add_weather(weather: Weather, session: Any) -> None:
        await weather.insert(session=session)

    
