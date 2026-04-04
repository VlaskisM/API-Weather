# Weather Dashboard API — План проекта

## Описание

FastAPI-приложение — погодный агрегатор. Пользователь добавляет города, сервис периодически
подтягивает погоду с OpenWeatherMap и хранит историю. Асинхронный httpx-клиент, фоновые задачи,
кэширование, **MongoDB** через **Motor** (async-драйвер) и **Beanie** (ODM на Pydantic).

**Архитектура — слоёная** (Layered Architecture):
```
Router (ручки) → Service (бизнес-логика) → Unit of Work (граница запроса, репозитории)
                                          → Repository (доступ к данным)
                                          → CachedWeatherRepository (обёртка с кэшем поверх репозитория погоды)
```

Сервисы **не создают** репозитории напрямую глобально: получают **`UnitOfWork`** (на один HTTP-запрос или один вызов из фоновой задачи) и вызывают `uow.cities`, `uow.weather` (или аналогичные имена). Так проще тестировать и при необходимости обернуть несколько операций в **транзакцию MongoDB** (например удаление города + связанных записей погоды).

---

## Структура проекта

```
API_weather/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app, lifespan
│   ├── config.py                  # Pydantic Settings (.env)
│   ├── database.py                # Motor client + init_beanie (подключение к MongoDB)
│   ├── models.py                  # Beanie Document: City, WeatherRecord
│   ├── schemas.py                 # Pydantic-схемы запросов/ответов
│   ├── cache.py                   # In-memory кэш с TTL
│   ├── weather_client.py          # httpx AsyncClient → OpenWeatherMap
│   ├── tasks.py                   # Фоновый сборщик погоды (asyncio)
│   ├── unit_of_work.py            # Unit of Work: репозитории + опционально ClientSession/транзакция
│   ├── dependencies.py            # FastAPI: get_uow и др. Depends()
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── city_repository.py     # CRUD по коллекции cities
│   │   └── weather_repository.py  # CRUD по коллекции weather_records
│   ├── services/
│   │   ├── __init__.py
│   │   ├── city_service.py        # Бизнес-логика городов
│   │   └── weather_service.py     # Бизнес-логика погоды + кэш-обёртка
│   └── routers/
│       ├── __init__.py
│       ├── cities.py              # Эндпоинты городов
│       └── weather.py             # Эндпоинты погоды
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── test_api.py
├── .env.example
├── requirements.txt
└── PLAN.md
```

---

## Слои и их ответственности

### Router (routers/) — Транспортный слой
- Принимает HTTP-запросы, валидирует входные данные через Pydantic-схемы
- Вызывает методы сервиса
- Формирует HTTP-ответы (статус-коды, headers)
- **Не содержит** бизнес-логики и прямых обращений к БД

### Service (services/) — Бизнес-логика
- Оркестрирует вызовы через **Unit of Work** (репозитории) и внешних клиентов (OWM, кэш)
- Содержит бизнес-правила (например: при добавлении города — геокодинг через OWM)
- Решает, откуда брать данные: кэш или БД
- **Не знает** про HTTP (никаких Request/Response)

### Unit of Work (`unit_of_work.py` + `dependencies.py`) — Граница работы с данными
- На **один запрос** (или одну итерацию фоновой задачи): создаётся экземпляр UoW, внутри — **CityRepository**, **WeatherRepository** (и при необходимости сессия Motor для транзакции)
- FastAPI: зависимость `get_uow` — `async def get_uow(): async with UnitOfWork() as uow: yield uow` (или фабрика без `async with`, если UoW не держит открытую транзакцию на весь запрос)
- **Сценарий с транзакцией:** `DELETE /api/cities/{id}` — внутри одной транзакции MongoDB удалить `WeatherRecord` по `city_id`, затем `City`; при ошибке — откат
- **Сценарий без транзакции:** простые CRUD — Beanie сам по себе; UoW всё равно даёт единую точку входа и тестовую заглушку
- Фоновая задача (`tasks.py`) создаёт UoW так же вручную (`async with UnitOfWork() ...`), а не через `Depends`

### Repository (repositories/) — Доступ к данным
- CRUD по коллекциям MongoDB через Beanie (Motor под капотом)
- Один репозиторий ≈ одна коллекция / один тип документа
- Уникальные поля и индексы — через `Settings` в Beanie или явное создание индексов при старте
- **Не знает** про бизнес-логику и внешние API

### CachedWeatherRepository (внутри weather_service.py) — Кэш-обёртка
- Декорирует `WeatherRepository` — сначала проверяет кэш, потом идёт в БД
- Прозрачна для сервиса: тот же интерфейс, что у репозитория
- Инвалидация при записи новых данных

---

## Поток данных (примеры)

### GET /api/weather/{city_id} — текущая погода
```
Router.get_current_weather(city_id)
  → WeatherService.get_current(uow, city_id)
      → cache.get(city_id)          # есть в кэше? → вернуть
      → uow.cities.get_by_id(...)  # координаты города
      → WeatherClient.fetch(lat, lon) # нет в кэше → запрос к OWM
      → uow.weather.save(record)    # сохранить в MongoDB
      → cache.set(city_id, data)     # положить в кэш
      → return data
```

### POST /api/cities — добавить город
```
Router.add_city(name)
  → CityService.add(uow, name)
      → WeatherClient.geocode(name)    # получить координаты
      → uow.cities.create(city)        # сохранить в MongoDB
      → return city
```

### DELETE /api/cities/{id} — с транзакцией (пример использования UoW)
```
CityService.delete(uow, city_id)
  → async with uow.transaction():      # опционально: MongoDB session + start_transaction
      → uow.weather.delete_by_city_id(city_id)
      → uow.cities.delete(city_id)
```

### Фоновый сборщик (tasks.py)
```
every 15 min:
  async with UnitOfWork() as uow:
      → cities = await uow.cities.get_all()
      → for city in cities:
          → WeatherClient.fetch(lat, lon)
          → await uow.weather.save(record)
          → cache.set(city_id, data)
```

---

## Модели данных (коллекции MongoDB)

### City (`cities`)
| Поле       | Тип            | Описание              |
|------------|----------------|-----------------------|
| _id        | ObjectId       | Идентификатор документа |
| name       | str (unique)   | Название города       |
| latitude   | float          | Широта (от OWM)       |
| longitude  | float          | Долгота (от OWM)      |
| created_at | datetime       | Дата добавления       |

### WeatherRecord (`weather_records`)
| Поле         | Тип       | Описание                        |
|--------------|-----------|---------------------------------|
| _id          | ObjectId  | Идентификатор документа         |
| city_id      | ObjectId  | Ссылка на документ City         |
| temperature  | float     | Температура (°C)                |
| feels_like   | float     | Ощущается как (°C)              |
| humidity     | int       | Влажность (%)                   |
| pressure     | int       | Давление (hPa)                  |
| wind_speed   | float     | Скорость ветра (м/с)            |
| description  | str       | Описание (например «облачно»)   |
| recorded_at  | datetime  | Время снятия данных             |

В API `city_id` в путях — строковое представление ObjectId (24 hex-символа), как принято в REST для MongoDB.

---

## API-эндпоинты

### Города (`/api/cities`)
| Метод  | Путь              | Описание                    |
|--------|-------------------|-----------------------------|
| GET    | `/api/cities`     | Список всех городов         |
| POST   | `/api/cities`     | Добавить город (по имени)   |
| DELETE | `/api/cities/{id}`| Удалить город и его историю |

### Погода (`/api/weather`)
| Метод | Путь                             | Описание                          |
|-------|----------------------------------|-----------------------------------|
| GET   | `/api/weather/{city_id}`         | Текущая погода (из кэша/OWM)     |
| GET   | `/api/weather/{city_id}/history` | История записей (query: from, to) |
| POST  | `/api/weather/refresh`           | Принудительное обновление всех    |

---

## Конфигурация (.env)

```env
OWM_API_KEY=your_openweathermap_api_key
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=weather_db
CACHE_TTL_SECONDS=300
FETCH_INTERVAL_SECONDS=900
```

(При необходимости — `mongodb+srv://...` для Atlas; учётные данные в URL или отдельными переменными.)

---

## Зависимости (requirements.txt)

```
fastapi>=0.110
uvicorn[standard]>=0.29
motor>=3.3
beanie>=1.25
httpx>=0.27
pydantic-settings>=2.2
python-dotenv>=1.0
pytest>=8.0
pytest-asyncio>=0.23
```

---

## Порядок реализации

1. **config + database** — настройки, Motor + `init_beanie`, регистрация документов и индексов
2. **models + schemas** — Beanie `Document` и Pydantic-схемы API
3. **repositories/** — CityRepository, WeatherRepository
4. **unit_of_work + dependencies** — класс `UnitOfWork` (связывает репозитории; опционально контекст транзакции), `get_uow` для FastAPI
5. **weather_client** — httpx-клиент к OpenWeatherMap
6. **cache** — простой TTL-кэш
7. **services/** — CityService, WeatherService принимают `UnitOfWork` (и другие зависимости); кэш-обёртка над погодой как сейчас
8. **routers/** — эндпоинты: `Depends(get_uow)` передаётся в сервисы
9. **tasks** — фоновый сборщик: явное создание UoW в цикле (не через `Depends`)
10. **main** — сборка приложения
11. **tests** — тесты API; подмена `get_uow` фейковым UoW или in-memory Mongo (по желанию)
