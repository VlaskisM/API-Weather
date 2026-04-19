from ast import Pass
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from src.clients import weather_client
from src.services.city_service import CityService


class DummyUoWContext:
    def __init__(self, uow):
        self._uow = uow

    async def __aenter__(self):
        return self._uow

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.fixture
def deps():

    cities = Mock()
    cities.get_by_name = AsyncMock()
    cities.add_city = AsyncMock()
    cities.get_all_citys = AsyncMock()
    cities.del_city = AsyncMock()

    uow = Mock()
    uow.cities = cities

    uow_factory = Mock(return_value=DummyUoWContext(uow))

    weather_client = Mock()
    weather_client.geocode = AsyncMock(return_value=(55.75, 37.62))

    service = CityService(uow_factory=uow_factory, weather_client=weather_client)
    return service, uow, cities, weather_client




@pytest.mark.asyncio
async def test_add_city_returns_none_if_exists(deps):
    service, uow, cities, weather_client = deps
    cities.get_by_name.return_value = SimpleNamespace(
        name_city="Moscow",
        latitude=55.75,
        longitude=37.62
    )

    result = await service.add_city("Moscow")

    assert result is None
    cities.get_by_name.assert_awaited_once_with("Moscow")
    weather_client.geocode.assert_not_awaited()
    cities.add_city.assert_not_awaited()


#@pytest.mark.asyncio
#async def test_add_city_creates_city_when_not_exists(deps):
#    service, uow, cities, weather_client = deps








