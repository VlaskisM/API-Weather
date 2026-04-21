from fastapi import APIRouter, HTTPException, Query

from src.clients.weather_client import CityNotFoundError, ServerErrorOWM, WeatherApiTimeoutError
from src.routes.depends import DepWeatherService
from src.schemas.schemas_weather import CurrentWeatherOut, WeatherRefreshOut

router = APIRouter(prefix="/weather", tags=["weather"])



@router.get("/", response_model=CurrentWeatherOut)
async def get_current_weather(
    weather_service: DepWeatherService,
    name_city: str = Query(...),
):
    try:
        return await weather_service.get_current_weather(name_city=name_city.strip().lower())
    except CityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except WeatherApiTimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e)) from e
    except ServerErrorOWM as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.get("/history/{name_city}")
async def get_history_weather(
    weather_service: DepWeatherService,
    name_city: str,
):
    weather =  await weather_service.get_history_weather(name_city = name_city.strip().lower())
    if weather:
        return weather
    else:
        raise HTTPException(status_code=400, detail="City not found")


@router.post("/refresh", response_model=WeatherRefreshOut)
async def refresh_weather(
    weather_service: DepWeatherService,
):
    return await weather_service.refresh_all_weather()
    
