# Docker Compose — полный конспект с кодом

> Справочник в стиле "скопировал блок -> запустил -> понял, почему работает".
> Акцент на `docker-compose.yml` для БД, брокеров сообщений и типовых backend-сценариев.

---

## Содержание

1. [Compose в двух словах](#1-compose-в-двух-словах)
2. [Базовый шаблон compose-файла](#2-базовый-шаблон-compose-файла)
3. [Ключевые секции и как они работают](#3-ключевые-секции-и-как-они-работают)
4. [PostgreSQL (база + healthcheck)](#4-postgresql-база--healthcheck)
5. [MySQL / MariaDB](#5-mysql--mariadb)
6. [MongoDB](#6-mongodb)
7. [Redis](#7-redis)
8. [RabbitMQ](#8-rabbitmq)
9. [Kafka (KRaft) и упрощенная альтернатива](#9-kafka-kraft-и-упрощенная-альтернатива)
10. [NATS (легкий брокер)](#10-nats-легкий-брокер)
11. [Celery стек: API + worker + beat + broker](#11-celery-стек-api--worker--beat--broker)
12. [Паттерны для dev/prod через profiles](#12-паттерны-для-devprod-через-profiles)
13. [Типичные ошибки и анти-паттерны](#13-типичные-ошибки-и-анти-паттерны)
14. [Команды отладки](#14-команды-отладки)
15. [Быстрая шпаргалка](#15-быстрая-шпаргалка)

---

## 1. Compose в двух словах

`Docker Compose` - это способ описать инфраструктуру проекта в YAML:

- какие контейнеры запускать;
- какие у них порты и переменные;
- как они связаны сетью;
- где хранить данные (volumes);
- в каком порядке ждать готовности (healthcheck + depends_on).

Логика простая:

```text
services -> контейнеры приложения
volumes  -> постоянные данные (БД, очереди)
networks -> изоляция и DNS между сервисами
```

---

## 2. Базовый шаблон compose-файла

```yaml
services:
  app:
    build: .
    command: uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload
    env_file:
      - .env
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  db:
    image: postgres:17
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
      interval: 5s
      timeout: 5s
      retries: 10
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

Что важно в этом шаблоне:

- `depends_on` с `service_healthy` работает только если у зависимого сервиса есть `healthcheck`;
- `env_file` удобно для app, но системные env для official DB image обычно задают через `environment`;
- без `volumes` данные БД исчезнут после `down -v`/пересоздания контейнера.

---

## 3. Ключевые секции и как они работают

### 3.1 `services`

Каждый сервис = отдельный контейнер.

```yaml
services:
  api:
    build: .
  redis:
    image: redis:7
```

Внутри сети Compose сервисы ходят друг к другу по имени:

- `api` подключается к Redis как `redis:6379`;
- не нужен `localhost` между контейнерами.

### 3.2 `ports` vs `expose`

```yaml
ports:
  - "5433:5432"   # хост:контейнер
expose:
  - "5432"        # только внутри docker-сети
```

- `ports` нужен, когда хочешь доступ с хоста (IDE, DBeaver, browser).
- `expose` - только межсервисный доступ, наружу не публикует.

### 3.3 `volumes`

```yaml
volumes:
  - pg_data:/var/lib/postgresql/data
```

- слева (`pg_data`) - именованный том;
- справа - путь внутри контейнера;
- удаление контейнера не удаляет том, пока явно не сделать `docker volume rm` или `down -v`.

### 3.4 `depends_on` и готовность

```yaml
depends_on:
  db:
    condition: service_healthy
```

Это не "дождаться, что БД полностью готова под миграции", а "healthcheck стал healthy".
Для надежности в приложении все равно нужен retry/backoff подключения.

### 3.5 `restart`

- `no` - не перезапускать;
- `on-failure` - только после падения;
- `unless-stopped` - оптимально для локальной разработки и серверов.

---

## 4. PostgreSQL (база + healthcheck)

```yaml
services:
  postgres:
    image: postgres:17
    container_name: api-weather-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME}
    ports:
      - "${DB_PORT:-5432}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./docker/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
      interval: 5s
      timeout: 5s
      retries: 10

volumes:
  postgres_data:
```

Разбор кода:

- `init.sql` выполнится только при "пустом" томе (первой инициализации);
- `${DB_PORT:-5432}` - если env не задан, берется `5432`;
- для прод лучше убрать `ports`, если к БД ходит только внутренний API.

Полезная проверка:

```bash
docker compose exec postgres psql -U "$DB_USER" -d "$DB_NAME" -c "select 1;"
```

---

## 5. MySQL / MariaDB

```yaml
services:
  mysql:
    image: mysql:8.4
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: ${MYSQL_DATABASE}
      MYSQL_USER: ${MYSQL_USER}
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
    ports:
      - "3306:3306"
    command: ["mysqld", "--default-authentication-plugin=mysql_native_password"]
    volumes:
      - mysql_data:/var/lib/mysql
    healthcheck:
      test: ["CMD-SHELL", "mysqladmin ping -h localhost -u${MYSQL_USER} -p${MYSQL_PASSWORD}"]
      interval: 5s
      timeout: 5s
      retries: 15

volumes:
  mysql_data:
```

Что помнить:

- MySQL дольше стартует, `retries` обычно нужен выше, чем у Postgres;
- `command` иногда необходим для совместимости старых клиентов.

MariaDB меняется почти только образом:

```yaml
image: mariadb:11
```

---

## 6. MongoDB

```yaml
services:
  mongo:
    image: mongo:7
    restart: unless-stopped
    environment:
      MONGO_INITDB_ROOT_USERNAME: ${MONGO_ROOT_USER}
      MONGO_INITDB_ROOT_PASSWORD: ${MONGO_ROOT_PASSWORD}
      MONGO_INITDB_DATABASE: ${MONGO_DB_NAME}
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db
    healthcheck:
      test:
        [
          "CMD-SHELL",
          "echo 'db.adminCommand(\"ping\").ok' | mongosh mongodb://$${MONGO_INITDB_ROOT_USERNAME}:$${MONGO_INITDB_ROOT_PASSWORD}@localhost:27017/admin --quiet"
        ]
      interval: 10s
      timeout: 5s
      retries: 10

volumes:
  mongo_data:
```

Разбор:

- `$${...}` - двойной `$`, чтобы Docker не подставил переменную на этапе compose-парсинга, а оставил shell внутри контейнера;
- `mongosh` в `healthcheck` - надежнее, чем просто проверка порта;
- URI для приложения обычно:
  `mongodb://user:pass@mongo:27017/mydb?authSource=admin`.

---

## 7. Redis

```yaml
services:
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: ["redis-server", "--appendonly", "yes", "--requirepass", "${REDIS_PASSWORD}"]
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "PING"]
      interval: 5s
      timeout: 3s
      retries: 20

volumes:
  redis_data:
```

Разбор:

- `appendonly yes` включает AOF persistence;
- без `--requirepass` Redis в dev-сети остается открытым для всех контейнеров;
- для кэша обычно достаточно Redis, для durable queue лучше брокеры сообщений.

---

## 8. RabbitMQ

```yaml
services:
  rabbitmq:
    image: rabbitmq:3.13-management
    restart: unless-stopped
    environment:
      RABBITMQ_DEFAULT_USER: ${RABBITMQ_USER}
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD}
      RABBITMQ_DEFAULT_VHOST: /
    ports:
      - "5672:5672"     # AMQP
      - "15672:15672"   # Web UI
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "ping"]
      interval: 10s
      timeout: 5s
      retries: 12

volumes:
  rabbitmq_data:
```

Разбор:

- `management` тег дает UI в браузере;
- `5672` нужен приложению, `15672` - только оператору;
- если Celery + RabbitMQ, URL вида:
  `amqp://user:pass@rabbitmq:5672//`.

---

## 9. Kafka (KRaft) и упрощенная альтернатива

Kafka в "чистом" виде конфигурируется сложно.
Для локальной разработки лучше использовать либо готовый KRaft-образ, либо Redpanda.

### 9.1 Kafka KRaft (одиночный узел)

```yaml
services:
  kafka:
    image: bitnami/kafka:3.7
    restart: unless-stopped
    environment:
      KAFKA_CFG_NODE_ID: 1
      KAFKA_CFG_PROCESS_ROLES: controller,broker
      KAFKA_CFG_CONTROLLER_QUORUM_VOTERS: 1@kafka:9093
      KAFKA_CFG_LISTENERS: PLAINTEXT://:9092,CONTROLLER://:9093
      KAFKA_CFG_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_CFG_LISTENER_SECURITY_PROTOCOL_MAP: CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT
      KAFKA_CFG_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_CFG_AUTO_CREATE_TOPICS_ENABLE: "true"
    ports:
      - "9092:9092"
    volumes:
      - kafka_data:/bitnami/kafka
    healthcheck:
      test: ["CMD-SHELL", "kafka-topics.sh --bootstrap-server localhost:9092 --list >/dev/null 2>&1"]
      interval: 10s
      timeout: 5s
      retries: 12

volumes:
  kafka_data:
```

### 9.2 Redpanda (Kafka API, проще для dev)

```yaml
services:
  redpanda:
    image: redpandadata/redpanda:v24.1.10
    command:
      - redpanda
      - start
      - --overprovisioned
      - --smp
      - "1"
      - --memory
      - "512M"
      - --reserve-memory
      - "0M"
      - --check=false
      - --node-id
      - "0"
      - --kafka-addr
      - PLAINTEXT://0.0.0.0:9092
      - --advertise-kafka-addr
      - PLAINTEXT://redpanda:9092
    ports:
      - "9092:9092"
      - "9644:9644"
    volumes:
      - redpanda_data:/var/lib/redpanda/data

volumes:
  redpanda_data:
```

Итог:

- хочешь "потрогать Kafka API быстро" -> Redpanda;
- хочешь ближе к production Kafka -> KRaft конфигурация.

---

## 10. NATS (легкий брокер)

```yaml
services:
  nats:
    image: nats:2.10-alpine
    command: ["-js", "-m", "8222"]
    ports:
      - "4222:4222"  # клиентский порт
      - "8222:8222"  # monitoring
    volumes:
      - nats_data:/data
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost:8222/healthz | grep -q ok"]
      interval: 5s
      timeout: 3s
      retries: 20

volumes:
  nats_data:
```

Когда выбирать NATS:

- нужен быстрый pub/sub и request/reply;
- инфраструктура должна быть легче Kafka;
- JetStream нужен как persistence-слой для сообщений.

---

## 11. Celery стек: API + worker + beat + broker

Ниже типовой compose для Python/FastAPI + Celery + Redis + Postgres.

```yaml
services:
  api:
    build: .
    command: uvicorn src.app:app --host 0.0.0.0 --port 8000
    env_file: [.env]
    ports: ["8000:8000"]
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

  worker:
    build: .
    command: celery -A src.celery_app worker -l info
    env_file: [.env]
    depends_on:
      redis:
        condition: service_healthy
      postgres:
        condition: service_healthy
    restart: unless-stopped

  beat:
    build: .
    command: celery -A src.celery_app beat -l info
    env_file: [.env]
    depends_on:
      redis:
        condition: service_healthy
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: ["redis-server", "--appendonly", "yes"]
    healthcheck:
      test: ["CMD", "redis-cli", "PING"]
      interval: 5s
      timeout: 3s
      retries: 20
    volumes:
      - redis_data:/data

  postgres:
    image: postgres:17
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
      interval: 5s
      timeout: 5s
      retries: 10
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  redis_data:
  postgres_data:
```

Разбор архитектуры:

- `api` принимает HTTP;
- `worker` выполняет фоновые задачи;
- `beat` планировщик периодических задач;
- `redis` транспорт очереди и, при желании, backend результатов;
- `postgres` хранит бизнес-данные приложения.

---

## 12. Паттерны для dev/prod через profiles

Один compose-файл, но разные режимы:

```yaml
services:
  api:
    build: .
    profiles: ["dev", "prod"]

  adminer:
    image: adminer
    ports: ["8080:8080"]
    profiles: ["dev"]

  flower:
    image: mher/flower
    command: celery --broker=${CELERY_BROKER_URL} flower
    ports: ["5555:5555"]
    profiles: ["dev"]
```

Запуск:

```bash
docker compose --profile dev up -d
docker compose --profile prod up -d
```

Идея:

- в `dev` поднимаешь UI-инструменты (`adminer`, `flower`, `kafka-ui`);
- в `prod` только нужные runtime-сервисы.

---

## 13. Типичные ошибки и анти-паттерны

1. **`localhost` внутри контейнера**
   - Из `api` нельзя ходить к `postgres` по `localhost`.
   - Нужно `postgres:5432` (имя сервиса).

2. **Неправильный healthcheck**
   - Проверка "порт открыт" не гарантирует готовность БД.
   - Используй нативные команды: `pg_isready`, `mysqladmin ping`, `mongosh ping`.

3. **Нет volume у БД**
   - После пересоздания контейнера теряешь данные.

4. **Секреты в compose**
   - Не коммить реальные пароли в `docker-compose.yml`.
   - Используй `.env` (локально) и secrets/CI vars (в прод).

5. **Ожидание, что `depends_on` решает все race-condition**
   - В приложении все равно нужен retry подключения к БД/брокеру.

6. **Один huge compose без профилей**
   - Лучше разделять через `profiles`, чтобы не поднимать лишнее.

---

## 14. Команды отладки

```bash
# Поднять в фоне
docker compose up -d

# Логи конкретного сервиса
docker compose logs -f postgres
docker compose logs -f rabbitmq

# Статус контейнеров
docker compose ps

# Перезапуск одного сервиса
docker compose restart redis

# Выполнить команду внутри контейнера
docker compose exec postgres psql -U "$DB_USER" -d "$DB_NAME"
docker compose exec mongo mongosh
docker compose exec rabbitmq rabbitmqctl list_queues

# Полная остановка
docker compose down

# Остановка + удаление томов (осторожно: данные удалятся)
docker compose down -v
```

Практика:

- если "все запущено, но не работает" - сначала `logs`, потом `exec`, потом проверка healthcheck;
- для БД проверяй подключение из приложения и из контейнера отдельно.

---

## 15. Быстрая шпаргалка

### Минимальные URI внутри docker-сети

- Postgres: `postgresql+asyncpg://user:pass@postgres:5432/dbname`
- MySQL: `mysql+pymysql://user:pass@mysql:3306/dbname`
- Mongo: `mongodb://user:pass@mongo:27017/dbname?authSource=admin`
- Redis: `redis://:password@redis:6379/0`
- RabbitMQ: `amqp://user:pass@rabbitmq:5672//`
- Kafka bootstrap: `kafka:9092`
- NATS: `nats://nats:4222`

### Что брать для какого кейса

- **Postgres** - реляционные данные, транзакции, сложные запросы.
- **MongoDB** - документоориентированные модели, гибкая схема.
- **Redis** - кэш, rate-limit, ephemeral state.
- **RabbitMQ** - надежные фоновые задачи, routing, retry/DLQ.
- **Kafka/Redpanda** - event streaming, большие потоки событий.
- **NATS** - легкий высокоскоростной messaging.

### Рабочий порядок настройки

1. Подними только БД/брокер.
2. Проверь healthcheck и подключение через `exec`.
3. Добавь API.
4. Добавь worker/background.
5. Добавь dev-инструменты через profiles.

---

Если нужно, следующим шагом могу сделать второй файл:
`theory/docker_compose_recipes.md` с "готовыми рецептами" под твой стек:

- FastAPI + Mongo + Beanie
- FastAPI + Postgres + Alembic
- FastAPI + Redis + Celery
- FastAPI + RabbitMQ + consumer
- FastAPI + Kafka producer/consumer