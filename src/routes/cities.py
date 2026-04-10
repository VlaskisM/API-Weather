from fastapi import APIRouter
from src.schemas import CityCreate

router = APIRouter(prefix="/cities", tags=["cities"])

uow = WeatherUnitOfWork(
    city_repository=CityRepository(),
    weather_repository=WeatherRepository(),
    city_service=CityService(),
    weather_service=WeatherService(),
)

@router.get("/")
async def get_cities():
    return {"message": "Cities"}



@router.post("/", response_model=CityCreate)
async def add_city(city: CityCreate):
    city = await uow.city_service.add(city)
    return city




