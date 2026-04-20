from typing import Annotated, Callable
from src.db.db_mongo import conn
from fastapi import Depends
from src.unit_of_work import UnitOfWork
from src.services.city_service import CityService
from src.clients.weather_client import WeatherClient
from src.db.db_redis import redis
from src.repositories.city_repository import CityRepository
from src.services.weather_service import WeatherService
from src.repositories.weather_repository import WeatherRepository


async def get_client():
    client = await conn.get_client()
    if client is None:
        raise RuntimeError("Mongo client is not initialized")
    return client


async def get_uow_factory(client=Depends(get_client)):
    return lambda: UnitOfWork(
        client=client,
        redis=redis,
        rep=CityRepository(),
        weather_rep=WeatherRepository()
        )

async def get_city_service(
    uow_factory: Callable[[], UnitOfWork] = Depends(get_uow_factory)
):
    return CityService(
        uow_factory=uow_factory,
        weather_client=WeatherClient()
    )

DepCityService = Annotated[CityService, Depends(get_city_service)]

async def get_weather_service(
    uow_factory: Callable[[], UnitOfWork] = Depends(get_uow_factory)
):
    return WeatherService(
        uow_factory=uow_factory,
        weather_client=WeatherClient()
    )

DepWeatherService = Annotated["WeatherService", Depends(get_weather_service)]







    
