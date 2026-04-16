from pydantic import BaseModel
from datetime import datetime

class CityCreate(BaseModel):

    name_city: str


class CityOutPut(CityCreate):
    latitude: float
    longitude: float
    