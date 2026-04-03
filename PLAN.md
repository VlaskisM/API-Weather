# Weather Dashboard API — План проекта

## Описание

FastAPI-приложение — погодный агрегатор. Пользователь добавляет города, сервис периодически
подтягивает погоду с OpenWeatherMap и хранит историю. Асинхронный httpx-клиент, фоновые задачи,
кэширование, PostgreSQL через SQLAlchemy async (asyncpg).

**Архитектура — слоёная** (Layered Architecture):
```
Router (ручки) → Service (бизнес-логика) → Repository (доступ к данным)
                                          → CachedRepository (обёртка с кэшем поверх репозитория)
```

---

## Структура проекта

```
API_weather/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app, lifespan
│   ├── config.py                  # Pydantic Settings (.env)
│   ├── database.py                # async SQLAlchemy engine + sessionmaker
│   ├── models.py                  # ORM: City, WeatherRecord
│   ├── schemas.py                 # Pydantic-схемы запросов/ответов
│   ├── cache.py                   # In-memory кэш с TTL
│   ├── weather_client.py          # httpx AsyncClient → OpenWeatherMap
│   ├── tasks.py                   # Фоновый сборщик погоды (asyncio)
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── city_repository.py     # CRUD операции с City в БД
│   │   └── weather_repository.py  # CRUD операции с WeatherRecord в БД
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
- Оркестрирует вызовы репозиториев и внешних клиентов
- Содержит бизнес-правила (например: при добавлении города — геокодинг через OWM)
- Решает, откуда брать данные: кэш или БД
- **Не знает** про HTTP (никаких Request/Response)

### Repository (repositories/) — Доступ к данным
- Чистые CRUD-операции с БД через SQLAlchemy + asyncpg (PostgreSQL)
- Один репозиторий = одна таблица
- Миграции через Alembic
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
  → WeatherService.get_current(city_id)
      → cache.get(city_id)          # есть в кэше? → вернуть
      → WeatherClient.fetch(lat, lon) # нет → запрос к OWM
      → WeatherRepository.save(record) # сохранить в БД
      → cache.set(city_id, data)     # положить в кэш
      → return data
```

### POST /api/cities — добавить город
```
Router.add_city(name)
  → CityService.add(name)
      → WeatherClient.geocode(name)    # получить координаты
      → CityRepository.create(city)    # сохранить в БД
      → return city
```

### Фоновый сборщик (tasks.py)
```
every 15 min:
  → CityRepository.get_all()
  → for city in cities:
      → WeatherClient.fetch(lat, lon)
      → WeatherRepository.save(record)
      → cache.set(city_id, data)
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

## Конфигурация (.env)

```env
OWM_API_KEY=your_openweathermap_api_key
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/weather_db
CACHE_TTL_SECONDS=300
FETCH_INTERVAL_SECONDS=900
```

---

## Зависимости (requirements.txt)

```
fastapi>=0.110
uvicorn[standard]>=0.29
sqlalchemy[asyncio]>=2.0
asyncpg>=0.30
httpx>=0.27
pydantic-settings>=2.2
python-dotenv>=1.0
alembic>=1.13
pytest>=8.0
pytest-asyncio>=0.23
```

---

## Порядок реализации

1. **config + database** — настройки, подключение к БД, создание таблиц
2. **models + schemas** — ORM-модели и Pydantic-схемы
3. **repositories/** — CityRepository, WeatherRepository
4. **weather_client** — httpx-клиент к OpenWeatherMap
5. **cache** — простой TTL-кэш
6. **services/** — CityService, WeatherService (с кэш-обёрткой)
7. **routers/** — эндпоинты городов и погоды
8. **tasks** — фоновый сборщик в lifespan
9. **main** — сборка приложения
10. **tests** — тесты API
