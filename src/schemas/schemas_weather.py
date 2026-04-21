from pydantic import BaseModel


class CurrentWeatherOut(BaseModel):
    name_city: str
    temperature: float
    feels_like: float
    humidity: int
    description: str
    wind_speed: float


class WeatherRefreshError(BaseModel):
    name_city: str
    reason: str


class WeatherRefreshOut(BaseModel):
    total_cities: int
    refreshed: int
    failed: int
    errors: list[WeatherRefreshError]
