from fastapi import APIRouter, HTTPException, Depends
from src.schemas import CityCreate
from src.services.city_service import CityService
from src.unit_of_work import UnitOfWork
from src.clients.weather_client import WeatherClient
from src.schemas.schemas_city import CityOutPut
from src.db import conn
from src.routes.depends import DepCityService

router = APIRouter(prefix="/cities", tags=["cities"])

city_service = CityService(
    uow_factory=UnitOfWork(),
    weather_client=WeatherClient(),
)

@router.get("/")
async def get_cities():
    return {"message": "Cities"}



@router.post("/", response_model=CityOutPut)
async def add_city(
    city: CityCreate,
    city_service: DepCityService
):
    city = await city_service.add_city(city.name_city)
    if city is None:
        raise HTTPException(status_code=400, detail="City already exists")
    return city