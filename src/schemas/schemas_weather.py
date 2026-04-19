from pydantic import BaseModel


class CurrentWeatherOut(BaseModel):
    name_city: str
    temperature: float
    feels_like: float
    humidity: int
    description: str
    wind_speed: float
