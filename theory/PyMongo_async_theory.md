# PyMongo Async — Полный конспект

> Справочник для быстрого поиска: открыл -> нашел -> применил.
> Акцент на асинхронный API `PyMongo`, работу с `ClientSession`, транзакциями и интеграцию с FastAPI.

---

## Содержание

1. [Что такое PyMongo Async](#1-что-такое-pymongo-async)
2. [Когда использовать PyMongo, а когда Beanie](#2-когда-использовать-pymongo-а-когда-beanie)
3. [Установка](#3-установка)
4. [Базовые сущности](#4-базовые-сущности)
5. [Подключение к MongoDB](#5-подключение-к-mongodb)
6. [Инициализация в FastAPI lifespan](#6-инициализация-в-fastapi-lifespan)
7. [База данных и коллекции](#7-база-данных-и-коллекции)
8. [CRUD в async PyMongo](#8-crud-в-async-pymongo)
9. [Фильтры и операторы](#9-фильтры-и-операторы)
10. [Курсоры и чтение результатов](#10-курсоры-и-чтение-результатов)
11. [Update-операции](#11-update-операции)
12. [Bulk-операции](#12-bulk-операции)
13. [Индексы](#13-индексы)
14. [AsyncClientSession](#14-asyncclientsession)
15. [Транзакции](#15-транзакции)
16. [Транзакции вручную через start_transaction](#16-транзакции-вручную-через-start_transaction)
17. [Транзакции через with_transaction](#17-транзакции-через-with_transaction)
18. [Unit of Work на PyMongo](#18-unit-of-work-на-pymongo)
19. [Репозиторий + UoW](#19-репозиторий--uow)
20. [Зависимости через FastAPI Depends](#20-зависимости-через-fastapi-depends)
21. [Типовые ошибки](#21-типовые-ошибки)
22. [Практические шаблоны](#22-практические-шаблоны)
23. [Шпаргалка](#23-шпаргалка)

---

## 1. Что такое PyMongo Async

`PyMongo` - официальный драйвер MongoDB для Python.

В современном `PyMongo` есть:

- синхронный API;
- асинхронный API;
- поддержка `MongoClient` / `AsyncMongoClient`;
- поддержка сессий;
- поддержка транзакций;
- низкоуровневый доступ без ODM.

Если `Beanie` скрывает часть деталей за моделями `Document`, то `PyMongo` дает прямой контроль над:

- коллекциями;
- фильтрами;
- транзакциями;
- уровнями concern;
- bulk-операциями;
- производительностью.

---

## 2. Когда использовать PyMongo, а когда Beanie

Используйте `PyMongo`, если:

- нужен максимальный контроль;
- хочется явно работать с коллекциями и документами;
- нужны сложные запросы и тонкая оптимизация;
- вы строите репозитории/UoW сами.

Используйте `Beanie`, если:

- хотите модели на `Pydantic`;
- нужен более удобный high-level API;
- проект document-oriented и хорошо ложится на ODM.

Частый паттерн:

- простые CRUD-ручки -> `Beanie`;
- сложные сценарии с транзакциями, bulk и специфической логикой -> `PyMongo`.

---

## 3. Установка

```bash
pip install pymongo
```

Если используете `.env` и FastAPI:

```bash
pip install pymongo fastapi uvicorn pydantic-settings
```

---

## 4. Базовые сущности

- `AsyncMongoClient` - клиент MongoDB.
- `database = client["my_db"]` - база данных.
- `collection = database["users"]` - коллекция.
- документ - обычный `dict`.
- фильтр - обычный `dict`.
- сессия - `AsyncClientSession`.
- транзакция - операции внутри `session.start_transaction()`.

Пример:

```python
from pymongo.asynchronous.mongo_client import AsyncMongoClient

client = AsyncMongoClient("mongodb://localhost:27017")
db = client["weather"]
cities = db["cities"]
```

---

## 5. Подключение к MongoDB

### Минимальный вариант

```python
from pymongo.asynchronous.mongo_client import AsyncMongoClient

client = AsyncMongoClient("mongodb://localhost:27017")
db = client["weather"]
collection = db["cities"]
```

### С настройками

```python
from pymongo.asynchronous.mongo_client import AsyncMongoClient

client = AsyncMongoClient(
    "mongodb://localhost:27017",
    maxPoolSize=100,
    minPoolSize=10,
    serverSelectionTimeoutMS=5000,
    socketTimeoutMS=5000,
    connectTimeoutMS=5000,
    retryWrites=True,
)
```

### Проверка подключения

```python
await client.admin.command({"ping": 1})
```

---

## 6. Инициализация в FastAPI lifespan

Лучший паттерн: один клиент на все приложение.

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pymongo.asynchronous.mongo_client import AsyncMongoClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = AsyncMongoClient("mongodb://localhost:27017")
    app.state.mongo_client = client
    app.state.db = client["weather"]

    try:
        await client.admin.command({"ping": 1})
        yield
    finally:
        await client.close()


app = FastAPI(lifespan=lifespan)
```

Почему так:

- не создаете новый клиент на каждый запрос;
- используете connection pool;
- легко доставать клиент через `Request` или `Depends`.

---

## 7. База данных и коллекции

```python
db = client["weather"]

cities = db["cities"]
users = db["users"]
logs = db["logs"]
```

Можно и так:

```python
db = client.weather
collection = db.cities
```

Но квадратные скобки чаще предпочтительнее:

- безопаснее для динамических имен;
- не конфликтуют с атрибутами объекта.

---

## 8. CRUD в async PyMongo

## Create

### `insert_one`

```python
doc = {
    "name_city": "Moscow",
    "latitude": 55.75,
    "longitude": 37.61,
}

result = await cities.insert_one(doc)
print(result.inserted_id)
```

### `insert_many`

```python
docs = [
    {"name_city": "Moscow", "latitude": 55.75, "longitude": 37.61},
    {"name_city": "London", "latitude": 51.50, "longitude": -0.12},
]

result = await cities.insert_many(docs)
print(result.inserted_ids)
```

## Read

### `find_one`

```python
city = await cities.find_one({"name_city": "Moscow"})
```

### `find`

```python
cursor = cities.find({"latitude": {"$gt": 50}})
items = await cursor.to_list(length=100)
```

## Delete

### `delete_one`

```python
result = await cities.delete_one({"name_city": "Moscow"})
print(result.deleted_count)
```

### `delete_many`

```python
result = await cities.delete_many({"obsolete": True})
print(result.deleted_count)
```

---

## 9. Фильтры и операторы

### Равенство

```python
await cities.find_one({"name_city": "Moscow"})
```

### Сравнение

```python
await cities.find({"temperature": {"$gt": 20}}).to_list(length=100)
await cities.find({"temperature": {"$gte": 20}}).to_list(length=100)
await cities.find({"temperature": {"$lt": 0}}).to_list(length=100)
```

### Логика

```python
await cities.find({
    "$and": [
        {"country": "RU"},
        {"temperature": {"$gt": 10}},
    ]
}).to_list(length=100)
```

```python
await cities.find({
    "$or": [
        {"country": "RU"},
        {"country": "GB"},
    ]
}).to_list(length=100)
```

### Наличие поля

```python
await cities.find({"latitude": {"$exists": True}}).to_list(length=100)
```

### По списку

```python
await cities.find({"country": {"$in": ["RU", "GB", "DE"]}}).to_list(length=100)
```

### Regex

```python
await cities.find({"name_city": {"$regex": "^Mos", "$options": "i"}}).to_list(length=100)
```

---

## 10. Курсоры и чтение результатов

`find()` возвращает курсор, а не сразу список.

```python
cursor = cities.find({"country": "RU"})
```

Получить список:

```python
docs = await cursor.to_list(length=100)
```

Итерироваться асинхронно:

```python
cursor = cities.find({})

async for doc in cursor:
    print(doc)
```

Сортировка, лимит, пропуск:

```python
docs = await (
    cities.find({})
    .sort("name_city", 1)
    .skip(20)
    .limit(10)
    .to_list(length=10)
)
```

---

## 11. Update-операции

### `update_one`

```python
result = await cities.update_one(
    {"name_city": "Moscow"},
    {"$set": {"country": "RU"}}
)

print(result.matched_count)
print(result.modified_count)
```

### `update_many`

```python
await cities.update_many(
    {"country": "RU"},
    {"$set": {"region": "Europe"}}
)
```

### `find_one_and_update`

Вернуть документ после обновления:

```python
from pymongo import ReturnDocument

doc = await cities.find_one_and_update(
    {"name_city": "Moscow"},
    {"$set": {"country": "RU"}},
    return_document=ReturnDocument.AFTER,
)
```

### Частые операторы обновления

```python
{"$set": {"name": "new"}}
{"$unset": {"deprecated_field": ""}}
{"$inc": {"counter": 1}}
{"$push": {"tags": "weather"}}
{"$addToSet": {"tags": "weather"}}
{"$pull": {"tags": "old"}}
```

---

## 12. Bulk-операции

Полезно, когда надо выполнить много операций за раз.

```python
from pymongo import InsertOne, UpdateOne, DeleteOne

operations = [
    InsertOne({"name_city": "Paris", "country": "FR"}),
    UpdateOne({"name_city": "Moscow"}, {"$set": {"country": "RU"}}),
    DeleteOne({"deprecated": True}),
]

result = await cities.bulk_write(operations, ordered=False)
print(result.inserted_count)
print(result.modified_count)
print(result.deleted_count)
```

---

## 13. Индексы

### Один индекс

```python
await cities.create_index("name_city", unique=True)
```

### Составной индекс

```python
from pymongo import ASCENDING, DESCENDING

await cities.create_index([
    ("country", ASCENDING),
    ("name_city", ASCENDING),
])
```

### TTL индекс

```python
await db["cache"].create_index("created_at", expireAfterSeconds=3600)
```

Индексы нужны для:

- быстрого поиска;
- уникальности;
- TTL-кеша;
- сортировки по индексируемым полям.

---

## 14. AsyncClientSession

Сессия - это логический контекст выполнения операций.

Сессия нужна для:

- транзакций;
- causally consistent reads;
- группировки последовательных операций.

Создание:

```python
session = await client.start_session()
```

Закрытие:

```python
await session.end_session()
```

Лучше через `async with`:

```python
async with await client.start_session() as session:
    ...
```

Важно:

- одна сессия не должна использоваться конкурентно;
- не надо шарить одну сессию между параллельными задачами;
- сессия должна использоваться с тем же клиентом, который ее создал.

---

## 15. Транзакции

Транзакция нужна, когда несколько операций должны пройти как единое целое:

- либо все изменения зафиксированы;
- либо ничего не сохранено.

Пример сценария:

- создаете заказ;
- уменьшаете остаток товара;
- пишете лог операции.

Если одна из операций упала, хотите откатить все.

Важно:

- транзакции поддерживаются на replica set / sharded cluster;
- на standalone MongoDB они не работают как полноценные multi-document transactions;
- все операции внутри транзакции должны получать `session=session`.

---

## 16. Транзакции вручную через start_transaction

Это лучший способ, если вы строите `UnitOfWork`.

### Самый наглядный шаблон

```python
async with await client.start_session() as session:
    async with session.start_transaction():
        await db["orders"].insert_one(
            {"order_id": 1, "status": "new"},
            session=session,
        )
        await db["inventory"].update_one(
            {"sku": "abc123", "qty": {"$gte": 1}},
            {"$inc": {"qty": -1}},
            session=session,
        )
```

Если внутри блока возникнет исключение:

- транзакция будет aborted;
- исключение пойдет выше.

Если все прошло успешно:

- транзакция будет committed при выходе из блока.

### Ручное управление через `__aenter__` / `__aexit__`

Это удобно, если вы пишете собственный UoW.

```python
session = await client.start_session()
tx = session.start_transaction()

try:
    await tx.__aenter__()

    await db["orders"].insert_one(
        {"order_id": 1, "status": "new"},
        session=session,
    )

    await db["inventory"].update_one(
        {"sku": "abc123", "qty": {"$gte": 1}},
        {"$inc": {"qty": -1}},
        session=session,
    )

    await tx.__aexit__(None, None, None)
except Exception as exc:
    await tx.__aexit__(type(exc), exc, exc.__traceback__)
    raise
finally:
    await session.end_session()
```

Это эквивалент `async with`, но вручную.

---

## 17. Транзакции через with_transaction

`with_transaction()` полезен, когда хотите встроенный retry некоторых транзиентных ошибок.

```python
async def txn_callback(session):
    orders = session.client["shop"]["orders"]
    inventory = session.client["shop"]["inventory"]

    await orders.insert_one(
        {"order_id": 1, "status": "new"},
        session=session,
    )

    await inventory.update_one(
        {"sku": "abc123", "qty": {"$gte": 1}},
        {"$inc": {"qty": -1}},
        session=session,
    )


async with await client.start_session() as session:
    await session.with_transaction(txn_callback)
```

Когда использовать:

- если не нужен сложный UoW;
- если хотите простой callback-based стиль;
- если устраивает, что callback может быть вызван повторно.

Важный нюанс:

- callback должен быть идемпотентным или безопасным к повторному запуску.

---

## 18. Unit of Work на PyMongo

Идея UoW:

- открыли сессию;
- открыли транзакцию;
- создали репозитории с этой сессией;
- выполнили бизнес-операции;
- commit или rollback;
- закрыли сессию.

Пример:

```python
from pymongo.asynchronous.mongo_client import AsyncMongoClient


class UnitOfWork:
    def __init__(self, client: AsyncMongoClient):
        self._client = client
        self._session = None
        self._tx_ctx = None
        self.users = None

    async def __aenter__(self):
        self._session = await self._client.start_session()
        self._tx_ctx = self._session.start_transaction()
        await self._tx_ctx.__aenter__()

        self.users = UserRepository(session=self._session)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc_type:
            await self.rollback()
        else:
            await self.commit()

        if self._tx_ctx is not None:
            await self._tx_ctx.__aexit__(exc_type, exc, tb)
        if self._session is not None:
            await self._session.end_session()

    async def commit(self):
        if self._session is None:
            raise RuntimeError("Session is not started")
        await self._session.commit_transaction()

    async def rollback(self):
        if self._session is None:
            raise RuntimeError("Session is not started")
        await self._session.abort_transaction()
```

Нюанс:

- либо управляете commit/abort через `session.commit_transaction()` / `abort_transaction()`;
- либо делегируете все `__aexit__` транзакции;
- лучше выбрать один единый стиль и не смешивать без понимания.

---

## 19. Репозиторий + UoW

### Репозиторий

```python
from pymongo.asynchronous.client_session import AsyncClientSession


class CityRepository:
    def __init__(self, collection, session: AsyncClientSession | None = None):
        self._collection = collection
        self._session = session

    async def get_by_name(self, name_city: str) -> dict | None:
        return await self._collection.find_one(
            {"name_city": name_city},
            session=self._session,
        )

    async def add_city(self, city: dict):
        await self._collection.insert_one(
            city,
            session=self._session,
        )
```

### Использование в сервисе

```python
class CityService:
    def __init__(self, uow_factory, weather_client):
        self._uow_factory = uow_factory
        self._weather_client = weather_client

    async def add_city(self, name_city: str):
        async with self._uow_factory() as uow:
            exists = await uow.cities.get_by_name(name_city)
            if exists:
                return None

            latitude, longitude = await self._weather_client.geocode(name_city)
            city = {
                "name_city": name_city,
                "latitude": latitude,
                "longitude": longitude,
            }

            await uow.cities.add_city(city)
            await uow.commit()
            return city
```

Главное правило:

- если репозиторий участвует в транзакции, каждая его операция должна передавать `session=self._session`.

---

## 20. Зависимости через FastAPI Depends

### Получить клиент

```python
from fastapi import Depends, Request


def get_mongo_client(request: Request):
    return request.app.state.mongo_client
```

### Фабрика UoW

```python
from collections.abc import Callable


def get_uow_factory(
    client=Depends(get_mongo_client),
) -> Callable[[], UnitOfWork]:
    return lambda: UnitOfWork(client=client)
```

### Сервис

```python
def get_city_service(
    uow_factory=Depends(get_uow_factory),
) -> CityService:
    return CityService(
        uow_factory=uow_factory,
        weather_client=WeatherClient(),
    )
```

### Endpoint

```python
@router.post("/cities")
async def add_city(
    payload: CityCreate,
    city_service: CityService = Depends(get_city_service),
):
    result = await city_service.add_city(payload.name_city)
    return result
```

Почему это хороший паттерн:

- клиент один на приложение;
- UoW новый на бизнес-операцию;
- нет проблем import-time initialization;
- сервис легко тестировать.

---

## 21. Типовые ошибки

### Ошибка 1. Создание клиента на каждый запрос

Плохо:

```python
@router.get("/")
async def handler():
    client = AsyncMongoClient("mongodb://localhost:27017")
    ...
```

Почему плохо:

- лишние подключения;
- сломанный pooling;
- лишняя нагрузка.

### Ошибка 2. Забыли передать `session`

Плохо:

```python
await orders.insert_one({"x": 1})
await inventory.update_one({"sku": "1"}, {"$inc": {"qty": -1}}, session=session)
```

Первая операция не войдет в транзакцию.

### Ошибка 3. Глобальное создание UoW до startup

Плохо:

```python
uow = UnitOfWork(client=get_client())
```

Если клиент еще не инициализирован, получите `None`.

### Ошибка 4. Параллельное использование одной сессии

Плохо:

```python
await asyncio.gather(
    col1.insert_one({"x": 1}, session=session),
    col2.insert_one({"y": 2}, session=session),
)
```

Сессию и транзакцию нужно использовать последовательно.

### Ошибка 5. Ожидание транзакций на standalone Mongo

Multi-document transactions требуют replica set или sharded cluster.

---

## 22. Практические шаблоны

### Шаблон: один клиент на приложение

```python
client = AsyncMongoClient(settings.mongo_url)
db = client[settings.MONGO_DB_NAME]
```

### Шаблон: репозиторий с session

```python
class BaseRepository:
    def __init__(self, collection, session=None):
        self.collection = collection
        self.session = session
```

### Шаблон: чтение по id

```python
from bson import ObjectId


async def get_by_id(collection, raw_id: str):
    return await collection.find_one({"_id": ObjectId(raw_id)})
```

### Шаблон: upsert

```python
await cities.update_one(
    {"name_city": "Moscow"},
    {"$set": {"country": "RU"}},
    upsert=True,
)
```

### Шаблон: атомарный счетчик

```python
doc = await db["counters"].find_one_and_update(
    {"_id": "city_seq"},
    {"$inc": {"value": 1}},
    upsert=True,
    return_document=True,
)
```

### Шаблон: транзакция через UoW

```python
async with uow_factory() as uow:
    await uow.orders.create(order_data)
    await uow.inventory.reserve_item(item_id, qty)
    await uow.commit()
```

---

## 23. Шпаргалка

### Подключение

```python
client = AsyncMongoClient("mongodb://localhost:27017")
db = client["weather"]
collection = db["cities"]
```

### CRUD

```python
await collection.insert_one({"name": "Moscow"})
doc = await collection.find_one({"name": "Moscow"})
await collection.update_one({"name": "Moscow"}, {"$set": {"country": "RU"}})
await collection.delete_one({"name": "Moscow"})
```

### Сессия

```python
async with await client.start_session() as session:
    ...
```

### Транзакция

```python
async with await client.start_session() as session:
    async with session.start_transaction():
        await collection.insert_one({"x": 1}, session=session)
```

### Фабрика UoW

```python
def get_uow_factory(client=Depends(get_mongo_client)):
    return lambda: UnitOfWork(client=client)
```

### Главное помнить

- `AsyncMongoClient` создаем один раз на приложение.
- Сессию создаем на бизнес-операцию.
- Все операции внутри транзакции должны получать `session=session`.
- Одну сессию не используем параллельно.
- Транзакции требуют replica set или sharded cluster.

---

## Что изучить дальше

После этого конспекта полезно углубиться в:

- `aggregation pipeline`;
- `read concern`, `write concern`, `read preference`;
- `change streams`;
- `bulk_write`;
- профилирование запросов и `explain()`;
- тестирование MongoDB-кода;
- паттерны `Repository` и `Unit of Work`.
