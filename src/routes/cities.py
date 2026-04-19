from fastapi import APIRouter, HTTPException, Query
from src.clients.weather_client import CityNotFoundError, ServerErrorOWM, WeatherApiTimeoutError
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
    try:
        city_item = await city_service.add_city(city.name_city.strip().lower())
        if city_item is None:
            raise HTTPException(status_code=400, detail="City already exists")
        return city_item
    except CityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except WeatherApiTimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e)) from e
    except ServerErrorOWM as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e



@router.get("/all", response_model=list[CityOutPut])
async def get_all_citys(
    city_service: DepCityService,
    limit: int = Query(5, ge=1, le=10),
    offset: int = Query(0, ge=0)
):
    return await city_service.get_all_citys(limit=limit, offset=offset)
    



@router.delete("/cities/{name_city}")
async def delete_city(
    name_city: str,
    city_service: DepCityService
):
    
    city_item = await city_service.del_city(name_city.strip().lower())
    if city_item:
        return city_item
    raise HTTPException(status_code=404, detail="City not found")
    

