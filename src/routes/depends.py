from typing import Annotated, Callable
from src.db import conn
from fastapi import Depends
from src.unit_of_work import UnitOfWork
from src.services.city_service import CityService
from src.clients.weather_client import WeatherClient


async def get_client():
    client = await conn.get_client()
    if client is None:
        raise RuntimeError("Mongo client is not initialized")
    return client


async def get_uow_factory(client=Depends(get_client)):
    return lambda: UnitOfWork(client=client)


async def get_city_service(
    uow_factory: Callable[[], UnitOfWork] = Depends(get_uow_factory)
):
    return CityService(
        uow_factory=uow_factory,
        weather_client=WeatherClient()
    )

DepCityService = Annotated[CityService, Depends(get_city_service)]



    
