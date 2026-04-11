from fastapi import APIRouter, HTTPException
from src.schemas import CityCreate
from src.services.city_service import CityService
from src.uow import UnitOfWork
from src.weather_client import WeatherClient
from src.schemas.schemas_city import CityOutPut

router = APIRouter(prefix="/cities", tags=["cities"])

city_service = CityService(
    uow=UnitOfWork(),
    weather_client=WeatherClient(),
)

@router.get("/")
async def get_cities():
    return {"message": "Cities"}



@router.post("/", response_model=CityOutPut)
async def add_city(city: CityCreate):
    city = await city_service.add_city(city.name_city)
    if city is None:
        raise HTTPException(status_code=400, detail="City already exists")

    return city