# Docker Compose: полная шпаргалка

Краткий и практичный справочник по `docker compose` (Compose V2).

---

## 1) Что такое Docker Compose

`Docker Compose` — инструмент для запуска **нескольких контейнеров** как одного приложения через YAML-файл (`docker-compose.yml`).

Типичные задачи:
- Поднять API + БД + кэш одной командой.
- Описать сети, тома, переменные окружения.
- Стандартизировать локальную разработку и CI.

Важно:
- Современный синтаксис: `docker compose ...` (с пробелом).
- Старый вариант `docker-compose ...` тоже встречается, но это legacy CLI.

---

## 2) Базовый compose-файл

```yaml
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      APP_ENV: dev
    depends_on:
      - db

  db:
    image: postgres:16
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app
      POSTGRES_DB: app
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

---

## 3) Структура `docker-compose.yml`

Основные секции:
- `services:` — контейнеры приложения.
- `volumes:` — именованные тома.
- `networks:` — пользовательские сети.
- `name:` — имя проекта (опционально).

Минимум:
- Достаточно `services`.
- Сети и тома можно добавлять по мере необходимости.

---

## 4) Ключи сервиса (самые важные)

### `image`
Использовать готовый образ:

```yaml
services:
  redis:
    image: redis:7-alpine
```

### `build`
Собрать образ из Dockerfile:

```yaml
services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        APP_VERSION: "1.0.0"
```

### `ports`
Проброс портов `HOST:CONTAINER`:

```yaml
ports:
  - "8080:80"
  - "127.0.0.1:5432:5432"
```

### `environment`
Переменные окружения контейнера:

```yaml
environment:
  APP_ENV: production
  LOG_LEVEL: info
```

### `env_file`
Подгрузка переменных из файла:

```yaml
env_file:
  - .env
```

### `volumes`
Монтирование томов/папок:

```yaml
volumes:
  - ./src:/app/src
  - appdata:/app/data
```

### `depends_on`
Порядок старта сервисов:

```yaml
depends_on:
  - db
  - redis
```

### `command` и `entrypoint`
Переопределить команду запуска:

```yaml
command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `restart`
Политика перезапуска:

```yaml
restart: unless-stopped
```

### `healthcheck`
Проверка здоровья:

```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 10s
```

### `profiles`
Условный запуск сервисов:

```yaml
profiles: ["debug"]
```

Запуск:
```bash
docker compose --profile debug up -d
```

---

## 5) Переменные и подстановка значений

### Файл `.env` для Compose-подстановки
Compose автоматически читает `.env` рядом с `docker-compose.yml`.

`.env`:
```env
APP_PORT=8000
PG_PORT=5432
TAG=latest
```

`docker-compose.yml`:
```yaml
services:
  api:
    image: my-api:${TAG}
    ports:
      - "${APP_PORT}:8000"
  db:
    image: postgres:16
    ports:
      - "${PG_PORT}:5432"
```

Формы:
- `${VAR}` — обязательная.
- `${VAR:-default}` — значение по умолчанию.
- `${VAR?error}` — ошибка, если переменная не задана.

---

## 6) Сети в Compose

По умолчанию Compose создает сеть проекта, и сервисы видят друг друга по имени:
- `http://api:8000`
- `postgres://db:5432/...`

Пользовательская сеть:

```yaml
services:
  api:
    networks: [backend]
  db:
    networks: [backend]

networks:
  backend:
    driver: bridge
```

---

## 7) Тома в Compose

### Именованный том (рекомендуется для данных БД)

```yaml
services:
  db:
    image: postgres:16
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

### Bind mount (удобно для разработки)

```yaml
services:
  api:
    volumes:
      - ./app:/app
```

---

## 8) Основные команды Compose

### Запуск/остановка

```bash
docker compose up
docker compose up -d
docker compose down
docker compose down -v
```

### Сборка

```bash
docker compose build
docker compose build --no-cache
docker compose up --build -d
```

### Логи и процессы

```bash
docker compose logs
docker compose logs -f
docker compose logs -f api
docker compose ps
docker compose top
```

### Выполнение команд внутри контейнера

```bash
docker compose exec api sh
docker compose exec db psql -U app -d app
docker compose run --rm api pytest
```

### Pull/Push образов

```bash
docker compose pull
docker compose push
```

### Проверка конфигурации

```bash
docker compose config
docker compose config --services
docker compose config --volumes
```

---

## 9) Несколько compose-файлов (override)

Базовый файл + dev override:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

Приоритет: параметры из последнего `-f` переопределяют предыдущие.

Частый паттерн:
- `docker-compose.yml` — общее.
- `docker-compose.dev.yml` — dev-тома, debug-порты, hot reload.
- `docker-compose.prod.yml` — production-настройки.

---

## 10) Зависимости и готовность сервисов

`depends_on` гарантирует порядок запуска, но не «готовность приложения».

Для готовности:
- Добавляй `healthcheck`.
- Используй ожидание в приложении (retry подключения к БД).

Пример с healthcheck у БД:

```yaml
services:
  db:
    image: postgres:16
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app"]
      interval: 5s
      timeout: 5s
      retries: 10
```

---

## 11) Масштабирование

```bash
docker compose up -d --scale worker=3
```

Примечания:
- Работает для stateless-сервисов.
- Не масштабируй сервис с фиксированным портом `HOST:CONTAINER` без балансировщика.

---

## 12) Частые ошибки

1. Порт уже занят:
- Измени левую часть в `ports`, например `8081:8000`.

2. Контейнер видит `localhost`, но это он сам:
- Для связи между сервисами используй имя сервиса (`db`, `redis`, `api`), а не `localhost`.

3. Переменная не подставилась:
- Проверь `.env`, синтаксис `${VAR}`, команду `docker compose config`.

4. Данные потерялись после `down`:
- Используй именованные тома и не запускай `down -v`, если не хочешь удалять данные.

5. `depends_on` не спас от race-condition:
- Добавь `healthcheck` + retry в коде.

---

## 13) Полезные one-liners

```bash
# Полностью поднять стек в фоне
docker compose up -d --build

# Перезапустить один сервис
docker compose restart api

# Посмотреть только имена сервисов
docker compose config --services

# Остановить и удалить все, включая тома
docker compose down -v

# Логи конкретного сервиса
docker compose logs -f worker
```

---

## 14) Production-практики (кратко)

- Закрепляй версии образов (`postgres:16.4`, не просто `latest`).
- Не храни секреты в Git (`.env` в `.gitignore`).
- Добавляй `healthcheck` и ограничения ресурсов (`deploy.resources` или параметры рантайма).
- Разделяй конфиги dev/prod (`-f` override, profiles).
- Регулярно делай backup данных томов БД.

---

## 15) Мини-шаблон для API + Postgres + RabbitMQ

```yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    env_file: [.env]
    environment:
      DATABASE_URL: postgres://app:app@db:5432/app
      RABBITMQ_URL: amqp://guest:guest@rabbitmq:5672/
    depends_on:
      - db
      - rabbitmq

  db:
    image: postgres:16
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app
      POSTGRES_DB: app
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app"]
      interval: 5s
      timeout: 5s
      retries: 10

  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5672:5672"
      - "15672:15672"

volumes:
  pgdata:
```

---

## 16) Быстрый старт (чеклист)

1. Создай `docker-compose.yml`.
2. Проверь конфиг: `docker compose config`.
3. Подними: `docker compose up -d --build`.
4. Проверь состояние: `docker compose ps`.
5. Смотри логи: `docker compose logs -f`.
6. Останови: `docker compose down`.

