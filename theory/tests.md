# Тесты в Python — полный конспект с упором на код

> Справочник формата "открыл -> нашел -> применил".
> Акцент на backend-практику: pytest, FastAPI, async, моки, MongoDB, httpx, Redis.

---

## Содержание

1. [Зачем вообще писать тесты](#1-зачем-вообще-писать-тесты)
2. [Пирамида тестов](#2-пирамида-тестов)
3. [Что такое pytest](#3-что-такое-pytest)
4. [Установка и структура проекта](#4-установка-и-структура-проекта)
5. [Первый тест и запуск](#5-первый-тест-и-запуск)
6. [Ассерты и падение теста](#6-ассерты-и-падение-теста)
7. [Фикстуры](#7-фикстуры)
8. [Параметризация](#8-параметризация)
9. [Маркеры и отбор тестов](#9-маркеры-и-отбор-тестов)
10. [Async тесты (pytest-asyncio)](#10-async-тесты-pytest-asyncio)
11. [Моки: Mock, MagicMock, AsyncMock](#11-моки-mock-magicmock-asyncmock)
12. [Патчинг: monkeypatch и unittest.mock.patch](#12-патчинг-monkeypatch-и-unittestmockpatch)
13. [Тестирование сервисного слоя](#13-тестирование-сервисного-слоя)
14. [Тестирование FastAPI эндпоинтов](#14-тестирование-fastapi-эндпоинтов)
15. [Тестирование с MongoDB (Beanie)](#15-тестирование-с-mongodb-beanie)
16. [Тестирование httpx клиентов](#16-тестирование-httpx-клиентов)
17. [Тестирование Redis](#17-тестирование-redis)
18. [Покрытие (coverage)](#18-покрытие-coverage)
19. [CI и скорость](#19-ci-и-скорость)
20. [Типичные ошибки](#20-типичные-ошибки)
21. [Быстрая шпаргалка](#21-быстрая-шпаргалка)

---

## 1. Зачем вообще писать тесты

- фиксируют поведение кода как исполняемую спецификацию;
- ловят регрессии при рефакторинге;
- ускоряют отладку: падает конкретный тест, а не "все сломалось";
- документация: тест показывает, как функцию реально зовут.

Правило: если боишься менять код - значит, тестов не хватает.

---

## 2. Пирамида тестов

- **Unit** - одна функция/класс, все зависимости замоканы. Быстрые, их много.
- **Integration** - модуль + реальная БД/кэш/HTTP. Медленнее, их меньше.
- **E2E** - поднятое приложение целиком, запросы через HTTP-клиент.

Практичное правило для backend-проекта:

- 70% unit на сервисы и утилиты;
- 20% integration (Mongo/Redis/httpx через тестовые инстансы);
- 10% E2E на ключевые сценарии (`/cities`, `/weather/{city}`).

---

## 3. Что такое pytest

`pytest` - де-факто стандартный тест-раннер в Python.

Ключевые фичи:

- плоские функции `def test_xxx(): ...` без классов;
- мощные фикстуры через DI;
- параметризация;
- богатая экосистема плагинов: `pytest-asyncio`, `pytest-cov`, `pytest-mock`, `httpx`.

---

## 4. Установка и структура проекта

### 4.1 Зависимости

```bash
pip install pytest pytest-asyncio pytest-cov pytest-mock httpx
```

### 4.2 Структура

```text
project/
  src/
    services/
      city_service.py
    main.py
  tests/
    conftest.py
    test_city_service.py
    test_api.py
  pytest.ini
```

### 4.3 pytest.ini

```ini
[pytest]
pythonpath = .
testpaths = tests
asyncio_mode = auto
addopts = -ra -q
markers =
    slow: медленные тесты
    integration: интеграционные тесты
```

`pythonpath = .` нужен, чтобы работали импорты вида `from src.services...`.

---

## 5. Первый тест и запуск

```python
# tests/test_math_basic.py
def add(a: int, b: int) -> int:
    return a + b

def test_add_positive():
    assert add(2, 3) == 5

def test_add_negative():
    assert add(-1, -1) == -2
```

Запуск:

```bash
pytest                       # все
pytest tests/test_math_basic.py
pytest -k "negative"         # по имени
pytest -x                    # стоп на первой ошибке
pytest -v                    # подробный вывод
```

---

## 6. Ассерты и падение теста

Pytest использует обычный `assert` и красиво раскрывает выражение.

```python
def test_dict_subset():
    user = {"id": 1, "name": "Max", "role": "admin"}
    assert user["role"] == "admin"
    assert "email" not in user
```

Проверка исключения:

```python
import pytest

def divide(a, b):
    if b == 0:
        raise ValueError("zero division")
    return a / b

def test_divide_zero():
    with pytest.raises(ValueError, match="zero"):
        divide(1, 0)
```

Проверка приближенных чисел:

```python
def test_float():
    assert 0.1 + 0.2 == pytest.approx(0.3)
```

---

## 7. Фикстуры

Фикстура - переиспользуемая "заготовка" данных/зависимости.

### 7.1 Локальная фикстура

```python
import pytest

@pytest.fixture
def sample_city():
    return {"name": "Moscow", "country": "RU"}

def test_city_name(sample_city):
    assert sample_city["name"] == "Moscow"
```

### 7.2 Общие фикстуры через conftest.py

`tests/conftest.py` автоматически виден всем тестам в папке.

```python
# tests/conftest.py
import pytest

@pytest.fixture
def user_payload():
    return {"id": 1, "name": "Max"}
```

### 7.3 Scope

```python
@pytest.fixture(scope="session")   # один раз на прогон
@pytest.fixture(scope="module")    # один раз на файл
@pytest.fixture(scope="function")  # по умолчанию, на каждый тест
```

### 7.4 Teardown через yield

```python
@pytest.fixture
def temp_file(tmp_path):
    path = tmp_path / "data.txt"
    path.write_text("hello")
    yield path
    # после теста: cleanup
    if path.exists():
        path.unlink()
```

---

## 8. Параметризация

Один тест - много входных данных.

```python
import pytest

@pytest.mark.parametrize(
    "a, b, expected",
    [
        (1, 2, 3),
        (0, 0, 0),
        (-1, 1, 0),
    ],
)
def test_add(a, b, expected):
    assert a + b == expected
```

С id для читаемости:

```python
@pytest.mark.parametrize(
    "city, valid",
    [
        ("Moscow", True),
        ("", False),
        ("   ", False),
    ],
    ids=["normal", "empty", "whitespace"],
)
def test_city_validation(city, valid):
    assert bool(city.strip()) is valid
```

---

## 9. Маркеры и отбор тестов

```python
import pytest

@pytest.mark.slow
def test_big_data():
    ...

@pytest.mark.integration
def test_real_mongo():
    ...
```

Запуск только нужных:

```bash
pytest -m "not slow"
pytest -m integration
```

Маркеры регистрируются в `pytest.ini`, иначе pytest ругается warning-ом.

---

## 10. Async тесты (pytest-asyncio)

FastAPI/Beanie/Redis - все async. Нужен `pytest-asyncio`.

С `asyncio_mode = auto` в `pytest.ini` писать маркер не надо:

```python
async def test_async_simple():
    import asyncio
    await asyncio.sleep(0)
    assert True
```

Без auto-режима:

```python
import pytest

@pytest.mark.asyncio
async def test_async_marked():
    assert 1 + 1 == 2
```

Async фикстуры:

```python
import pytest_asyncio

@pytest_asyncio.fixture
async def redis_fake():
    client = FakeRedis()
    await client.ping()
    yield client
    await client.aclose()
```

---

## 11. Моки: Mock, MagicMock, AsyncMock

Мок подменяет зависимость, которая "тяжелая" или внешняя.

### 11.1 Mock vs MagicMock vs AsyncMock

- `Mock` - базовый, синхронный.
- `MagicMock` - поддерживает магические методы (`__len__`, `__iter__`).
- `AsyncMock` - возвращает awaitable, нужен для async-функций.

### 11.2 Пример: подмена репозитория

```python
from unittest.mock import AsyncMock, Mock

class CityService:
    def __init__(self, repo):
        self.repo = repo

    async def get_city(self, name: str):
        city = await self.repo.find_by_name(name)
        if city is None:
            raise ValueError("not found")
        return city

async def test_get_city_ok():
    repo = Mock()
    repo.find_by_name = AsyncMock(return_value={"name": "Moscow"})

    service = CityService(repo)
    result = await service.get_city("Moscow")

    assert result["name"] == "Moscow"
    repo.find_by_name.assert_awaited_once_with("Moscow")
```

### 11.3 Возвращать разные значения

```python
mock = AsyncMock(side_effect=[1, 2, 3])
await mock()   # 1
await mock()   # 2
```

Бросить исключение:

```python
mock = AsyncMock(side_effect=ValueError("boom"))
```

### 11.4 Проверка вызовов

```python
mock.assert_called_once()
mock.assert_called_with("Moscow")
mock.assert_not_called()
assert mock.call_count == 2
```

---

## 12. Патчинг: monkeypatch и unittest.mock.patch

### 12.1 monkeypatch (встроен в pytest)

Подходит для env-переменных и атрибутов модулей.

```python
def test_env(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")
    import os
    assert os.environ["API_KEY"] == "test-key"
```

Подмена функции в модуле:

```python
def test_patch_func(monkeypatch):
    from src.services import city_service
    monkeypatch.setattr(city_service, "now", lambda: "2026-04-17")
```

### 12.2 patch из unittest.mock

Подмена по строковому пути (важно: путь там, где ИСПОЛЬЗУЕТСЯ, а не где объявлено).

```python
from unittest.mock import patch, AsyncMock

async def test_patch_external():
    with patch("src.services.city_service.fetch_weather", new=AsyncMock(return_value={"t": 20})):
        from src.services.city_service import get_weather
        result = await get_weather("Moscow")
        assert result["t"] == 20
```

Декоратором:

```python
@patch("src.services.city_service.fetch_weather", new_callable=AsyncMock)
async def test_with_decorator(mock_fetch):
    mock_fetch.return_value = {"t": 20}
    ...
```

---

## 13. Тестирование сервисного слоя

Сервис = бизнес-логика. Репозиторий/HTTP-клиент/кэш - моки.

Пример под наш проект:

```python
# src/services/city_service.py
class CityService:
    def __init__(self, repo, cache):
        self.repo = repo
        self.cache = cache

    async def list_cities(self, page: int, size: int):
        key = f"cache:cities:{page}:{size}"
        cached = await self.cache.get(key)
        if cached:
            return cached
        items = await self.repo.list(page=page, size=size)
        await self.cache.set(key, items, ex=60)
        return items
```

Тест:

```python
import pytest
from unittest.mock import AsyncMock

from src.services.city_service import CityService

async def test_list_cities_cache_hit():
    cache = AsyncMock()
    cache.get.return_value = [{"name": "Moscow"}]
    repo = AsyncMock()

    service = CityService(repo=repo, cache=cache)
    result = await service.list_cities(1, 10)

    assert result == [{"name": "Moscow"}]
    repo.list.assert_not_called()   # из БД не ходили

async def test_list_cities_cache_miss():
    cache = AsyncMock()
    cache.get.return_value = None
    repo = AsyncMock()
    repo.list.return_value = [{"name": "Tver"}]

    service = CityService(repo=repo, cache=cache)
    result = await service.list_cities(1, 10)

    assert result == [{"name": "Tver"}]
    cache.set.assert_awaited_once()
    repo.list.assert_awaited_once_with(page=1, size=10)
```

---

## 14. Тестирование FastAPI эндпоинтов

### 14.1 TestClient (sync)

```python
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
```

### 14.2 httpx.AsyncClient (async, рекомендуется)

```python
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

async def test_get_city(client):
    r = await client.get("/cities/Moscow")
    assert r.status_code == 200
```

### 14.3 Переопределение зависимостей

Главный трюк FastAPI - `app.dependency_overrides`:

```python
from src.main import app
from src.deps import get_city_service

class FakeCityService:
    async def list_cities(self, page, size):
        return [{"name": "FakeCity"}]

def override():
    return FakeCityService()

async def test_list_cities_mocked(client):
    app.dependency_overrides[get_city_service] = override
    try:
        r = await client.get("/cities?page=1&size=10")
        assert r.json() == [{"name": "FakeCity"}]
    finally:
        app.dependency_overrides.clear()
```

---

## 15. Тестирование с MongoDB (Beanie)

Два подхода.

### 15.1 Мокать репозиторий

Для unit-тестов сервиса - просто `AsyncMock` вместо коллекции. См. раздел 13.

### 15.2 Интеграционные тесты с реальной Mongo

Варианты:

- отдельный контейнер Mongo в docker-compose для тестов;
- `mongomock-motor` для sync-совместимого мокирования;
- эфемерная тестовая БД с префиксом `test_`.

Пример фикстуры с реальной тестовой БД:

```python
import pytest_asyncio
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from src.models.city import City

@pytest_asyncio.fixture
async def mongo():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["test_weather"]
    await init_beanie(database=db, document_models=[City])
    yield db
    await client.drop_database("test_weather")
    client.close()

async def test_create_city(mongo):
    city = City(name="Moscow", country="RU")
    await city.insert()
    found = await City.find_one(City.name == "Moscow")
    assert found is not None
```

Важно: интеграционные тесты помечай `@pytest.mark.integration`, чтобы в CI можно было отделять.

---

## 16. Тестирование httpx клиентов

Когда код ходит во внешний API через `httpx.AsyncClient`.

### 16.1 respx - мок для httpx

```bash
pip install respx
```

```python
import httpx
import respx

@respx.mock
async def test_fetch_weather():
    route = respx.get("https://api.weather.test/Moscow").mock(
        return_value=httpx.Response(200, json={"temp": 20.5})
    )

    async with httpx.AsyncClient() as c:
        r = await c.get("https://api.weather.test/Moscow")

    assert route.called
    assert r.json()["temp"] == 20.5
```

### 16.2 Через MockTransport

```python
import httpx

def handler(request):
    return httpx.Response(200, json={"ok": True})

async def test_with_transport():
    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as c:
        r = await c.get("https://anything.test/x")
        assert r.json() == {"ok": True}
```

---

## 17. Тестирование Redis

### 17.1 fakeredis

```bash
pip install fakeredis
```

```python
import pytest_asyncio
from fakeredis.aioredis import FakeRedis

@pytest_asyncio.fixture
async def redis_client():
    client = FakeRedis(decode_responses=True)
    yield client
    await client.aclose()

async def test_cache_roundtrip(redis_client):
    await redis_client.set("cache:x", "42", ex=60)
    assert await redis_client.get("cache:x") == "42"
```

### 17.2 Реальный Redis в Docker

Если важна совместимость с Lua/Streams - поднимай настоящий Redis как отдельный сервис в `docker-compose.test.yml`.

---

## 18. Покрытие (coverage)

```bash
pip install pytest-cov
pytest --cov=src --cov-report=term-missing
pytest --cov=src --cov-report=html   # открой htmlcov/index.html
```

В `pytest.ini` или `pyproject.toml`:

```ini
[pytest]
addopts = --cov=src --cov-report=term-missing
```

Порог:

```bash
pytest --cov=src --cov-fail-under=80
```

Coverage - не самоцель. Метрика "100% покрыто" без ассертов = ноль пользы.

---

## 19. CI и скорость

- `pytest -n auto` (`pytest-xdist`) - тесты параллельно.
- Отделяй unit от integration через маркеры и два job-а в CI.
- Кэшируй `.pytest_cache` и зависимости между прогонами.
- В PR-gate гоняй только unit, интеграцию на merge в master.

Пример GitHub Actions шаг:

```yaml
- name: Run tests
  run: pytest -m "not integration" --cov=src --cov-fail-under=80
```

---

## 20. Типичные ошибки

1. **Тест тестирует мок, а не код**
   - мок возвращает то, что тест ждет, и ничего не проверяет.

2. **Один огромный тест "все сразу"**
   - падает - неясно, что именно сломано. Дроби.

3. **Патчишь не там, где используется**
   - `patch("httpx.get")` вместо `patch("src.services.weather.httpx.get")`.

4. **Async-функция замокана через `Mock`, а не `AsyncMock`**
   - получишь `coroutine was never awaited` или `MagicMock can't be awaited`.

5. **Тесты зависят друг от друга**
   - один меняет глобальное состояние, другой падает. Scope фикстур и cleanup.

6. **Интеграционные тесты в unit-наборе**
   - медленно и хрупко. Разделяй маркерами.

7. **Нет cleanup тестовой БД**
   - следующий прогон видит старые данные, тесты флапают.

8. **Мокаешь `datetime.now` напрямую**
   - лучше внедрять clock-зависимость в сервис и подменять ее в тесте.

9. **Ассерт `assert result` вместо `assert result == expected`**
   - проходит на любой truthy-значение, ничего не ловит.

10. **Забытый `await` в тесте**
    - тест зеленый, а код по факту не выполнился.

---

## 21. Быстрая шпаргалка

### 21.1 Команды

```bash
pytest                          # все
pytest -k "name"                # по подстроке
pytest -x --lf                  # стоп + только упавшие
pytest -m "not slow"            # без медленных
pytest --cov=src                # coverage
pytest -n auto                  # параллельно
pytest -s                       # не глотать print
pytest --pdb                    # дебаггер при падении
```

### 21.2 Базовый async unit-тест с моками

```python
from unittest.mock import AsyncMock
from src.services.city_service import CityService

async def test_something():
    repo = AsyncMock()
    repo.find_by_name.return_value = {"name": "Moscow"}

    service = CityService(repo=repo, cache=AsyncMock())
    result = await service.get_city("Moscow")

    assert result["name"] == "Moscow"
    repo.find_by_name.assert_awaited_once_with("Moscow")
```

### 21.3 Что выбрать для задач

- чистая функция/сервис -> unit + AsyncMock;
- FastAPI endpoint -> `httpx.AsyncClient` + `ASGITransport` + `dependency_overrides`;
- внешний HTTP-API -> `respx` или `MockTransport`;
- Redis -> `fakeredis` для unit, реальный Redis для integration;
- MongoDB -> моки репозитория для unit, отдельная тестовая БД для integration;
- долгие/внешние тесты -> маркер `@pytest.mark.integration` и отдельный job в CI.

### 21.4 Мини-чеклист перед коммитом

1. `pytest -x` локально зеленый.
2. Новый код покрыт хотя бы одним happy path + одним edge case.
3. Нет `time.sleep` и сетевых походов в unit-тестах.
4. Нет закомментированных тестов.
5. Маркеры проставлены там, где тест медленный/интеграционный.
