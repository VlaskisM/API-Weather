from pydantic import BaseModel
from datetime import datetime

class CityCreate(BaseModel):

    name_city: str
    created_at: datetime


class CityOutPut(CityCreate):
    latitude: float
    longitude: float
    