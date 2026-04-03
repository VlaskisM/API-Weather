# Weather Dashboard API — План проекта

## Описание

FastAPI-приложение — погодный агрегатор. Пользователь добавляет города, сервис периодически
подтягивает погоду с OpenWeatherMap и хранит историю. Асинхронный httpx-клиент, фоновые задачи,
кэширование, SQLite через SQLAlchemy async.

---

## Структура проекта

```
API_weather/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, lifespan (запуск фоновых задач)
│   ├── config.py             # Pydantic Settings (.env)
│   ├── database.py           # async SQLAlchemy engine + sessionmaker
│   ├── models.py             # ORM: City, WeatherRecord
│   ├── schemas.py            # Pydantic-схемы запросов/ответов
│   ├── weather_client.py     # httpx AsyncClient → OpenWeatherMap
│   ├── cache.py              # In-memory кэш с TTL
│   ├── tasks.py              # Фоновый сборщик погоды (asyncio)
│   └── routers/
│       ├── __init__.py
│       ├── cities.py         # CRUD городов
│       └── weather.py        # Текущая погода + история
├── tests/
│   ├── __init__.py
│   ├── conftest.py           # Фикстуры: тестовая БД, клиент
│   └── test_api.py           # Тесты эндпоинтов
├── .env.example
├── requirements.txt
└── PLAN.md
```

---

## Модели данных

### City
| Поле       | Тип          | Описание              |
|------------|--------------|-----------------------|
| id         | int (PK)     | Автоинкремент         |
| name       | str (unique) | Название города       |
| latitude   | float        | Широта (от OWM)       |
| longitude  | float        | Долгота (от OWM)      |
| created_at | datetime     | Дата добавления       |

### WeatherRecord
| Поле         | Тип       | Описание                        |
|--------------|-----------|---------------------------------|
| id           | int (PK)  | Автоинкремент                   |
| city_id      | int (FK)  | Ссылка на City                  |
| temperature  | float     | Температура (°C)                |
| feels_like   | float     | Ощущается как (°C)              |
| humidity     | int       | Влажность (%)                   |
| pressure     | int       | Давление (hPa)                  |
| wind_speed   | float     | Скорость ветра (м/с)            |
| description  | str       | Описание (например «облачно»)   |
| recorded_at  | datetime  | Время снятия данных             |

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

## Ключевые компоненты

### 1. weather_client.py — HTTP-клиент
- `httpx.AsyncClient` с таймаутами и retry
- Методы: `get_current_weather(lat, lon)`, `geocode_city(name)`
- Обработка ошибок OWM (лимиты, невалидный город)

### 2. cache.py — In-memory кэш
- Словарь `{city_id: (data, timestamp)}`
- TTL = 5 минут (настраивается)
- `get(city_id)` / `set(city_id, data)` / `invalidate(city_id)`

### 3. tasks.py — Фоновый сборщик
- Запускается через `asyncio.create_task` в lifespan
- Цикл: каждые 15 минут обходит все города, запрашивает погоду, сохраняет в БД
- Обновляет кэш при каждом запросе
- Graceful shutdown через `asyncio.Event`

### 4. database.py — Async SQLAlchemy
- `aiosqlite` как драйвер (sqlite+aiosqlite)
- `async_sessionmaker` для DI через `Depends`

---

## Конфигурация (.env)

```env
OWM_API_KEY=your_openweathermap_api_key
DATABASE_URL=sqlite+aiosqlite:///./weather.db
CACHE_TTL_SECONDS=300
FETCH_INTERVAL_SECONDS=900
```

---

## Зависимости (requirements.txt)

```
fastapi>=0.110
uvicorn[standard]>=0.29
sqlalchemy[asyncio]>=2.0
aiosqlite>=0.20
httpx>=0.27
pydantic-settings>=2.2
python-dotenv>=1.0
pytest>=8.0
pytest-asyncio>=0.23
httpx  # также используется как test client
```

---

## Порядок реализации

1. **config + database** — настройки, подключение к БД, создание таблиц
2. **models + schemas** — ORM-модели и Pydantic-схемы
3. **weather_client** — httpx-клиент к OpenWeatherMap API
4. **cache** — простой TTL-кэш
5. **routers/cities** — CRUD городов
6. **routers/weather** — получение погоды и истории
7. **tasks** — фоновый сборщик в lifespan
8. **main** — сборка приложения, подключение роутеров
9. **tests** — тесты API

---

## Чему научит

- **httpx AsyncClient** — асинхронные HTTP-запросы к внешним API
- **Фоновые задачи** — asyncio tasks с graceful shutdown через lifespan
- **Кэширование** — in-memory кэш с TTL, инвалидация
- **SQLAlchemy async** — асинхронная работа с БД
- **Pydantic Settings** — конфигурация через .env
- **Dependency Injection** — сессии БД, клиент через Depends
