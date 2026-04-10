# MongoDB для бэкенда: теория, Docker, Motor, Beanie и структура проекта

Документ для конспекта: основы Mongo, **полный** `docker-compose` для Mongo, асинхронный стек **Motor + Beanie**, и как **разнести код по файлам** (конфиг, подключение к БД, внешние клиенты, операции с данными, сервисы, роуты).

---

## 1. MongoDB кратко

- **Документная** NoSQL БД: данные в **коллекциях** как **документы** (BSON ≈ JSON + типы вроде `ObjectId`, `Date`).
- **База** — логический контейнер коллекций. Часто одна БД на приложение (`api_weather`), внутри коллекции `cities`, `weather_records`.
- Лимит одного документа — **16 МБ**.
- Нет таблиц и JOIN как в SQL; связи — **вложение** в документ или **ссылка** (`_id` другого документа) + `$lookup` в aggregation.

| SQL            | Mongo        |
|----------------|--------------|
| Таблица        | Коллекция    |
| Строка         | Документ     |
| Колонка        | Поле         |

---

## 2. Полный `docker-compose.yml` для Mongo

Ниже готовый файл для локальной разработки: порт, том для данных, опциональный root-пользователь, healthcheck, именованный volume внизу файла.

```yaml
services:
  mongo:
    image: mongo:7
    container_name: api-weather-mongo
    restart: unless-stopped
    ports:
      - "27017:27017"
    environment:
      MONGO_INITDB_ROOT_USERNAME: root
      MONGO_INITDB_ROOT_PASSWORD: secret
    volumes:
      - mongo_data:/data/db
    healthcheck:
      test: ["CMD", "mongosh", "--quiet", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 20s

volumes:
  mongo_data:
```

### Зачем каждая часть

| Ключ | Назначение |
|------|------------|
| `services.mongo` | Имя сервиса в Compose (для `docker compose up mongo`). |
| `image: mongo:7` | Официальный образ MongoDB 7. |
| `container_name` | Удобное имя контейнера в `docker ps`. |
| `restart: unless-stopped` | Автоперезапуск, пока ты сам не остановил. |
| `ports: "27017:27017"` | С хоста `localhost:27017` → в контейнер. |
| `environment` | При **первом** создании тома задаёт root (`root` / `secret`). Без этих переменных Mongo поднимается **без** auth (только для простого локального теста). |
| `volumes: mongo_data:/data/db` | Данные БД в Docker volume; при пересоздании контейнера данные сохраняются. `/data/db` — стандартный путь данных в образе `mongo`. |
| `healthcheck` | Проверка, что `mongod` отвечает (удобно для `depends_on: condition: service_healthy`). |

### Запуск

```bash
cd путь/к/проекту
docker compose up -d mongo
docker compose ps
docker compose logs -f mongo
```

### `.env` для приложения (с auth как выше)

```env
MONGO_URL=mongodb://root:secret@localhost:27017/?authSource=admin
MONGO_DB=api_weather
```

### Вариант без логина (только учеба)

Убери блок `environment` и используй:

```env
MONGO_URL=mongodb://localhost:27017
```

---

## 3. Разделение логики по файлам (бэкенд)

Идея: **роут** не знает про BSON, **сервис** не знает про HTTP, **репозиторий** только про коллекции, **один клиент БД** на приложение.

### Рекомендуемая схема папок (пример под `src/`)

```
src/
├── config.py              # Pydantic Settings: MONGO_URL, MONGO_DB, ключи API
├── db.py                  # Жизненный цикл Mongo: клиент, get_database(), init_beanie, close
├── models/                # Только Beanie Document (схема коллекций)
│   ├── __init__.py
│   ├── city.py
│   └── weather_record.py
├── schemas/               # Pydantic: тела запросов/ответов API (не путать с Document)
│   ├── __init__.py
│   └── city.py
├── repositories/          # «Операции» с БД: CRUD, фильтры (без бизнес-правил HTTP)
│   ├── __init__.py
│   └── city_repository.py
├── services/              # Бизнес-логика: оркестрация репозиториев + внешних клиентов
│   ├── __init__.py
│   └── city_service.py
├── clients/               # Внешние HTTP/API (не Mongo!): OpenWeather, платежи и т.д.
│   ├── __init__.py
│   └── weather_client.py
├── routes/                # FastAPI: Depends, вызов сервиса, статус-коды
│   ├── __init__.py
│   └── cities.py
└── app.py                 # FastAPI app, lifespan, include_router
```

### Кто за что отвечает

| Файл / слой | Ответственность |
|-------------|-----------------|
| **config.py** | Читает `.env`, валидирует настройки (`MONGO_URL`, `OWM_API_KEY`, …). |
| **db.py** | Создаёт `AsyncIOMotorClient`, отдаёт `database`, при Beanie — `await init_beanie(...)`, на shutdown — `client.close()`. Здесь **нет** бизнес-логики. |
| **clients/** | Клиенты к **внешним** сервисам (`httpx.AsyncClient` → OpenWeather). Не путать с «Mongo client»: это отдельный модуль. |
| **repositories/** | Только доступ к данным: `insert`, `find`, `update`, `delete` (через Motor коллекции или Beanie модели). |
| **services/** | Правила: «нельзя дублировать город», «после добавления города — запланировать погоду», вызов репозитория + `weather_client`. |
| **routes/** | HTTP: парсинг запроса, `Depends`, вызов сервиса, формирование ответа. |
| **models/** (Beanie) | Структура документа в Mongo + индексы в `Settings`. |
| **schemas/** (Pydantic) | Контракт API (вход/выход), можно отличать от внутренней модели БД. |

### Поток запроса

```
HTTP → routes → services → repositories → Mongo
                    ↘ clients → внешний API
```

### Альтернатива без Beanie

Те же папки; в **repositories** используешь `db["cities"]` и `await collection.insert_one({...})` вместо `Document.insert()`.

---

## 4. Motor — что это

**Motor** — официальный **асинхронный** драйвер для MongoDB в Python. Под капотом совместим с **PyMongo**, API похож, операции через **`await`**.

- Пакет в `requirements.txt`: **`motor`** (не `pymotor`).
- Импорт клиента: `from motor.motor_asyncio import AsyncIOMotorClient`.

### Минимальный `db.py` (только Motor)

```python
from motor.motor_asyncio import AsyncIOMotorClient

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    if _client is None:
        raise RuntimeError("Mongo client is not initialized")
    return _client


async def connect_mongo(uri: str) -> None:
    global _client
    _client = AsyncIOMotorClient(uri)
    await _client.admin.command("ping")


async def close_mongo() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


def get_database(name: str):
    return get_client()[name]
```

В `lifespan` FastAPI: `await connect_mongo(settings.MONGO_URL)` → `yield` → `await close_mongo()`.

### Операции на коллекции (без Beanie)

```python
db = get_database("api_weather")
cities = db["cities"]
await cities.insert_one({"name": "Moscow"})
doc = await cities.find_one({"name": "Moscow"})
```

---

## 5. Beanie — что это и связь с Motor

**Beanie** — **async ODM** на **Pydantic v2**: модели документов как классы, запросы `await User.find_one(...)`. Работает **только поверх Motor** (`AsyncIOMotorClient` + объект базы).

1. Описываешь класс `Document`.
2. При старте приложения вызываешь **`await init_beanie(database=db, document_models=[City, ...])`**.
3. В репозитории или сервисе вызываешь методы модели.

### Инициализация в `lifespan`

```python
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from src.models.city import City  # пример пути

async def lifespan(app):
    client = AsyncIOMotorClient(settings.MONGO_URL)
    db = client[settings.MONGO_DB]
    await init_beanie(database=db, document_models=[City])
    app.state.mongo_client = client
    yield
    client.close()
```

### Пример модели

```python
from beanie import Document, Indexed


class City(Document):
    name: Indexed(str, unique=True)

    class Settings:
        name = "cities"
```

### Пример «операции» в сервисе/репозитории

```python
city = City(name="Moscow")
await city.insert()
found = await City.find_one(City.name == "Moscow")
```

### Motor vs Beanie

| | Motor напрямую | Beanie |
|---|----------------|--------|
| Схема | Словари / ручная валидация | Классы + Pydantic |
| Запросы | `collection.find_one({...})` | `Model.find_one(Model.field == x)` |
| Индексы | `create_index` вручную | Часто в `Settings` / `Indexed` |

---

## 6. Базовые сущности Mongo

- **`_id`** — первичный ключ; по умолчанию `ObjectId`.
- **Коллекция** — не требует заранее заданной схемы (валидацию можно включить в БД).

---

## 7. CRUD в mongosh (кратко)

```javascript
use api_weather
db.cities.insertOne({ name: "Moscow" })
db.cities.find()
db.cities.findOne({ name: "Moscow" })
db.cities.updateOne({ name: "Moscow" }, { $set: { country: "RU" } })
db.cities.deleteOne({ name: "Moscow" })
```

Операторы фильтра: `$gt`, `$gte`, `$lt`, `$in`, `$or`, `$exists`, и т.д.

---

## 8. CRUD в PyMongo / Motor (идея)

Те же операции: `insert_one`, `find_one`, `update_one` с `$set`, `delete_one`. В Motor всё с **`await`**.

---

## 9. Индексы

Ускоряют чтение и сортировку, замедляют запись.

```javascript
db.cities.createIndex({ name: 1 }, { unique: true })
```

В Beanie — `Indexed` или `Settings.indexes`.

Проверка плана: `find(...).explain("executionStats")` — искать `IXSCAN` вместо `COLLSCAN`.

---

## 10. Aggregation

Цепочка этапов: `$match`, `$group`, `$project`, `$sort`, `$lookup` (связь коллекций).

---

## 11. Embedding vs referencing

- **Вложение** — связанные данные в одном документе (быстрее читать целиком, лимит 16 МБ).
- **Ссылка** — `city_id` в другой коллекции (нормализация, несколько запросов или `$lookup`).

---

## 12. Транзакции

Несколько операций атомарно — через `client.start_session()` и `start_transaction()` (нужен replica set в проде). В простом одноузловом Docker часто без транзакций обходятся или поднимают replica set отдельно.

---

## 13. Безопасность

- Auth, сеть, TLS в проде.
- Секреты в `.env`, не в git.
- Бэкапы и проверка восстановления.

---

## 14. Полезные ссылки

- MongoDB: [https://www.mongodb.com/docs/](https://www.mongodb.com/docs/)
- Motor: [https://motor.readthedocs.io/](https://motor.readthedocs.io/)
- Beanie: [https://beanie-odm.dev/](https://beanie-odm.dev/)
- PyMongo: [https://www.mongodb.com/docs/languages/python/pymongo-driver/current/](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/)

---

*Файл можно дополнять схемами коллекций своего проекта и примерами запросов из логов.*
