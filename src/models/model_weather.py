from beanie import Document, Indexed


class Weather(Document):
    name_city: Indexed(str)
    temperature: float
    feels_like: float
    humidity: int
    description: str
    wind_speed: float

    class Settings:
        name = "weather"