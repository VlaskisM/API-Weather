from abc import ABC, abstractmethod
from typing import Any, List
from src.models.model_weather import Weather



class AbstractWeatherRepository(ABC):
    
    @abstractmethod
    async def add_weather(self, weather: Weather, session: Any) -> None:
        pass

    @abstractmethod
    async def get_by_name(self, name_city: str, session: Any) -> Weather | None:
        pass

    @abstractmethod
    async def get_history_weather(self, name_city: str, session: Any) -> List[Weather]:
        pass

    @abstractmethod
    async def delete_history_by_name(self, name_city: str, session: Any) -> int:
        pass


    

class WeatherRepository(AbstractWeatherRepository):
    

    async def add_weather(self, weather: Weather, session: Any) -> None:
        return await weather.insert(session=session)

    async def get_by_name(self, name_city: str, session: Any) -> Weather | None:
        return await Weather.find_one(Weather.name_city == name_city, session=session)

    async def get_history_weather(self, name_city: str, session: Any) -> List[Weather]:
        return await Weather.find(Weather.name_city == name_city, session=session).to_list()

    async def delete_history_by_name(self, name_city: str, session: Any) -> int:
        weather_items = await Weather.find(Weather.name_city == name_city, session=session).to_list()
        for weather in weather_items:
            await weather.delete(session=session)
        return len(weather_items)

    
