# API Weather

FastAPI сервис для работы с городами и погодой:
- хранит список городов в MongoDB;
- кеширует данные в Redis;
- получает текущую погоду через OpenWeatherMap API.

## Стек

- Python 3.11+
- FastAPI
- MongoDB (Beanie + PyMongo)
- Redis
- Docker Compose (для MongoDB и Redis)

## Архитектура

Проект построен по слоям, чтобы изолировать HTTP, бизнес-логику и доступ к данным.

### Слои

- `src/routes` - HTTP слой (FastAPI endpoints, валидация входа, HTTP-коды).
- `src/services` - бизнес-логика use-case'ов (`CityService`, `WeatherService`).
- `src/unit_of_work.py` - единая точка сборки репозиториев на один use-case.
- `src/repositories` - доступ к данным (Mongo + Redis кеш).
- `src/clients` - внешние API клиенты (OpenWeatherMap).
- `src/models` - ODM-модели Beanie (`City`, `Weather`).
- `src/schemas` - DTO/response модели.
- `src/db` - подключение к Mongo/Redis.
- `src/config.py` - настройки из `.env`.

### Поток запроса

1. HTTP запрос приходит в роут (`src/routes`).
2. Роут берет сервис через dependency (`src/routes/depends.py`).
3. Сервис открывает `UnitOfWork`.
4. `UnitOfWork` выдает репозитории:
   - `CacheCityRepository`
   - `CacheWeatherRepository`
5. Репозитории:
   - сначала читают/пишут Redis;
   - при промахе идут в Mongo (Beanie);
   - при необходимости вызывают `WeatherClient` для OWM.
6. Сервис возвращает DTO, роут отдает HTTP-ответ.

### Структура проекта

```text
src/
  app.py                 # FastAPI app + lifespan
  run.py                 # локальный запуск uvicorn
  config.py              # pydantic-settings
  unit_of_work.py        # сборка репозиториев для use-case
  clients/
    weather_client.py    # OpenWeatherMap client
  db/
    db_mongo.py          # init/close Mongo
    db_redis.py          # Redis client
  routes/
    depends.py           # DI провайдеры сервисов/uow
    cities.py            # /cities endpoints
    weather.py           # /weather endpoints
  services/
    city_service.py
    weather_service.py
  repositories/
    city_repository.py
    city_repository_cache.py
    weather_repository.py
    weather_repository_cache.py
  models/
    model_city.py
    model_weather.py
  schemas/
    schemas_city.py
    schemas_weather.py
```

## Быстрый старт

1. Клонируйте проект и перейдите в директорию:
   - `E:\VisualStudioCodeProjects\API_weather`
2. Создайте и активируйте виртуальное окружение:
   - Windows PowerShell:
     - `python -m venv .venv`
     - `.venv\Scripts\Activate.ps1`
3. Установите зависимости:
   - `pip install -r requirements.txt`
4. Поднимите инфраструктуру:
   - `docker compose up -d`
5. Запустите API:
   - `python -m src.run`

Swagger UI:
- `http://127.0.0.1:8000/docs`


## Переменные окружения

Проект читает настройки из файла `.env`:

- `MONGO_PORT`
- `MONGO_HOST`
- `MONGO_DB_NAME`
- `MONGO_INITDB_ROOT_USERNAME`
- `MONGO_INITDB_ROOT_PASSWORD`
- `REDIS_HOST`
- `REDIS_PORT`
- `OWM_API_KEY`
- `OWM_URL`
- `OWM_WEATHER_URL`

Примечание:
- в текущей конфигурации проект работает без Mongo транзакций (без `replicaSet` в `mongo_url`).
- для возврата транзакций нужно поднять replica set и включить сессии в `UnitOfWork`.

## Основные ручки

### Cities

- `GET /cities/` - техническая проверка роутера.
- `POST /cities/` - добавить город.
- `GET /cities/all?limit=5&offset=0` - получить список городов.
- `DELETE /cities/{name_city}` - удалить город.

### Weather

- `GET /weather/?name_city=moscow` - текущая погода по городу.
- `GET /weather/history/{name_city}` - история погоды по городу.
- `POST /weather/refresh` - обновить погоду для всех городов.

## Примеры запросов

Добавить город:

```bash
curl -X POST "http://127.0.0.1:8000/cities/" \
  -H "Content-Type: application/json" \
  -d "{\"name_city\":\"moscow\"}"
```

Получить текущую погоду:

```bash
curl "http://127.0.0.1:8000/weather/?name_city=moscow"
```

## Остановка

- Остановить API: `Ctrl+C`
- Остановить контейнеры: `docker compose down`
- Остановить контейнеры и удалить volume Mongo: `docker compose down -v`
