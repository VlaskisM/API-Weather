from beanie import Document, Indexed
from datetime import datetime
from pydantic import Field


class City(Document):
    name_city: Indexed(str, unique=True)
    created_at: datetime = Field(default_factory=datetime.now)
    latitude: float
    longitude: float

    class Settings:
        name = "cities"

