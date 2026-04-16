from fastapi import APIRouter, HTTPException
from src.schemas import CityCreate
from src.schemas.schemas_city import CityOutPut
from src.routes.depends import DepCityService

router = APIRouter(prefix="/cities", tags=["cities"])


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