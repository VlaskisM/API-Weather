# Redis — полный конспект с упором на код

> Справочник формата "открыл -> нашел -> применил".
> Акцент на backend-практику: Python, FastAPI, кэш, очереди, блокировки, Pub/Sub, Streams.

---

## Содержание

1. [Что такое Redis](#1-что-такое-redis)
2. [Когда Redis нужен, а когда нет](#2-когда-redis-нужен-а-когда-нет)
3. [Установка и запуск](#3-установка-и-запуск)
4. [Базовые сущности](#4-базовые-сущности)
5. [Подключение из Python](#5-подключение-из-python)
6. [Основные команды и типы данных](#6-основные-команды-и-типы-данных)
7. [TTL и политика истечения](#7-ttl-и-политика-истечения)
8. [Кэширование в FastAPI](#8-кэширование-в-fastapi)
9. [Cache-aside и write-through паттерны](#9-cache-aside-и-write-through-паттерны)
10. [Rate limiting](#10-rate-limiting)
11. [Distributed lock](#11-distributed-lock)
12. [Pub/Sub](#12-pubsub)
13. [Redis Streams (очереди)](#13-redis-streams-очереди)
14. [Транзакции и Lua-скрипты](#14-транзакции-и-lua-скрипты)
15. [Пайплайны и производительность](#15-пайплайны-и-производительность)
16. [Persistence: RDB и AOF](#16-persistence-rdb-и-aof)
17. [Redis в Docker Compose](#17-redis-в-docker-compose)
18. [Настройки для production](#18-настройки-для-production)
19. [Типичные ошибки](#19-типичные-ошибки)
20. [Быстрая шпаргалка](#20-быстрая-шпаргалка)

---

## 1. Что такое Redis

`Redis` - in-memory key-value хранилище с очень быстрыми операциями.

Ключевая идея:

- данные хранятся в RAM;
- операции обычно O(1) или близко;
- подходит для кэша, счетчиков, очередей, временных данных.

Redis это не только "кэш":

- кэш ответов API;
- сессии и токены;
- rate limit;
- pub/sub;
- очереди задач (в т.ч. через Streams);
- распределенные блокировки.

---

## 2. Когда Redis нужен, а когда нет

Используй Redis, если:

- есть дорогие вычисления/внешние API и нужен кэш;
- нужно ограничивать частоту запросов;
- нужна легкая очередь/событийная шина;
- нужны атомарные инкременты счетчиков.

Не используй Redis как основную БД "вместо всего", если:

- нужны сложные реляционные запросы;
- нужна надежная долговечность бизнес-данных уровня Postgres;
- нужен audit trail "ничего не теряется".

Практичное правило:

- `Postgres/Mongo` -> источник истины;
- `Redis` -> ускоритель и временное состояние.

---

## 3. Установка и запуск

### 3.1 Локально через Docker

```bash
docker run --name redis-local -p 6379:6379 redis:7-alpine
```

С паролем и AOF:

```bash
docker run --name redis-local \
  -p 6379:6379 \
  redis:7-alpine \
  redis-server --appendonly yes --requirepass secret123
```

### 3.2 Python зависимости

```bash
pip install redis
```

Для FastAPI часто достаточно этого пакета: у него есть sync и async API.

---

## 4. Базовые сущности

- `key` - строковый ключ;
- `value` - строка/число/структура (set/hash/list/zset/stream);
- `TTL` - время жизни ключа;
- namespace через префиксы: `user:42`, `weather:moscow`.

Базовые паттерны ключей:

```text
cache:weather:city:moscow
rate:login:ip:1.2.3.4
session:user:42
queue:notifications
```

Префиксы дают:

- читаемость;
- меньше конфликтов;
- удобный поиск при отладке.

---

## 5. Подключение из Python

### 5.1 Sync клиент

```python
import redis

r = redis.Redis(
    host="localhost",
    port=6379,
    db=0,
    password="secret123",
    decode_responses=True,  # сразу str, а не bytes
)

r.ping()
```

### 5.2 Async клиент (рекомендуется для FastAPI)

```python
from redis.asyncio import Redis

redis_client = Redis(
    host="localhost",
    port=6379,
    db=0,
    password="secret123",
    decode_responses=True,
)

await redis_client.ping()
```

### 5.3 URI формат

```text
redis://:password@redis:6379/0
```

`/0` - номер logical DB.

---

## 6. Основные команды и типы данных

## 6.1 String

```python
await redis_client.set("app:version", "1.0.0")
value = await redis_client.get("app:version")
```

С TTL:

```python
await redis_client.set("cache:key", "payload", ex=60)  # 60 секунд
```

## 6.2 Counter

```python
await redis_client.incr("stats:requests")
await redis_client.incrby("stats:bytes", 1024)
```

## 6.3 Hash

```python
await redis_client.hset("user:42", mapping={"name": "Max", "role": "admin"})
user = await redis_client.hgetall("user:42")
```

## 6.4 List (очередь FIFO)

```python
await redis_client.rpush("queue:emails", "task1", "task2")
task = await redis_client.lpop("queue:emails")
```

## 6.5 Set (уникальные элементы)

```python
await redis_client.sadd("online:users", "42", "99")
is_online = await redis_client.sismember("online:users", "42")
```

## 6.6 Sorted Set (приоритет/рейтинг)

```python
await redis_client.zadd("leaderboard", {"alice": 1200, "bob": 980})
top = await redis_client.zrevrange("leaderboard", 0, 9, withscores=True)
```

---

## 7. TTL и политика истечения

TTL - главный механизм кэша.

Проверка:

```python
ttl = await redis_client.ttl("cache:key")
```

Продление:

```python
await redis_client.expire("cache:key", 120)
```

Удаление:

```python
await redis_client.delete("cache:key")
```

Практика:

- кэш API: `30-300` секунд;
- справочники: `10-60` минут;
- сессии: по бизнес-требованию.

Важно: не ставь "вечный" кэш без стратегии инвалидиации.

---

## 8. Кэширование в FastAPI

Ниже минимальный async пример.

```python
import json
from fastapi import FastAPI
from redis.asyncio import Redis

app = FastAPI()
redis_client: Redis | None = None

@app.on_event("startup")
async def startup():
    global redis_client
    redis_client = Redis(host="redis", port=6379, decode_responses=True)

@app.on_event("shutdown")
async def shutdown():
    if redis_client:
        await redis_client.close()

@app.get("/weather/{city}")
async def get_weather(city: str):
    cache_key = f"cache:weather:{city.lower()}"

    cached = await redis_client.get(cache_key)
    if cached is not None:
        return json.loads(cached)

    # здесь запрос во внешний API/БД
    data = {"city": city, "temp": 20.5, "source": "api"}

    await redis_client.set(cache_key, json.dumps(data), ex=120)
    return data
```

Идея:

- сначала читаем из Redis;
- если miss, берем из источника истины;
- кладем в Redis с TTL.

---

## 9. Cache-aside и write-through паттерны

### 9.1 Cache-aside (самый популярный)

Read flow:

1. попробовать `GET` из Redis;
2. miss -> прочитать из БД;
3. записать в Redis с TTL;
4. вернуть ответ.

Write flow:

1. записать в БД;
2. удалить/обновить ключ в Redis.

Плюсы:

- простой;
- кэшируется только реально запрошенное.

Минус:

- первый запрос после истечения TTL будет медленнее.

### 9.2 Write-through

При записи одновременно обновляешь БД и кэш.
Подходит, когда важно, чтобы кэш всегда был "горячим" после write.

---

## 10. Rate limiting

### 10.1 Fixed window (простой вариант)

```python
from fastapi import HTTPException

async def check_rate_limit(redis_client, key: str, limit: int, window_sec: int) -> None:
    current = await redis_client.incr(key)
    if current == 1:
        await redis_client.expire(key, window_sec)
    if current > limit:
        raise HTTPException(status_code=429, detail="Too many requests")
```

Пример ключа:

`rate:login:ip:1.2.3.4`

### 10.2 Sliding window / token bucket

Точнее, но сложнее. Обычно делают через Lua или готовые библиотеки.
Для большинства API fixed window достаточно на старте.

---

## 11. Distributed lock

Когда нужен lock:

- важно не выполнять одну и ту же задачу параллельно в нескольких воркерах;
- нужно "лидерство" одной инстанции.

Базовый вариант:

```python
lock = redis_client.lock("lock:refresh_weather", timeout=30)
acquired = await lock.acquire(blocking=False)
if not acquired:
    return {"status": "skip", "reason": "already running"}

try:
    # критическая секция
    ...
finally:
    await lock.release()
```

Важно:

- всегда ставь `timeout`;
- в `finally` освобождай lock;
- для high-critical distributed lock изучай Redlock и ограничения сети/часов.

---

## 12. Pub/Sub

Хорошо для realtime-уведомлений, но не для гарантированной доставки.

Publisher:

```python
await redis_client.publish("events:weather", '{"city":"Moscow","temp":22}')
```

Subscriber:

```python
pubsub = redis_client.pubsub()
await pubsub.subscribe("events:weather")

async for message in pubsub.listen():
    if message["type"] == "message":
        print("event:", message["data"])
```

Ограничение pub/sub:

- если подписчик был offline, сообщение потеряно.

Если нужна надежная доставка - чаще выбирают Streams/Rabbit/Kafka.

---

## 13. Redis Streams (очереди)

Streams - встроенный журнал сообщений с consumer groups.

Producer:

```python
message_id = await redis_client.xadd(
    "stream:orders",
    {"order_id": "123", "status": "created"},
)
```

Создание группы:

```python
await redis_client.xgroup_create(
    name="stream:orders",
    groupname="workers",
    id="0",
    mkstream=True,
)
```

Consumer:

```python
messages = await redis_client.xreadgroup(
    groupname="workers",
    consumername="worker-1",
    streams={"stream:orders": ">"},
    count=10,
    block=5000,
)

for stream_name, items in messages:
    for msg_id, payload in items:
        # обработка
        ...
        await redis_client.xack("stream:orders", "workers", msg_id)
```

Плюсы Streams:

- есть хранение сообщений;
- есть ack и pending;
- можно строить retry-механику.

---

## 14. Транзакции и Lua-скрипты

### 14.1 MULTI/EXEC через pipeline(transaction=True)

```python
pipe = redis_client.pipeline(transaction=True)
pipe.incr("counter:a")
pipe.incr("counter:b")
result = await pipe.execute()
```

Это атомарное выполнение набора команд (на уровне Redis event loop).

### 14.2 Lua для атомарной бизнес-логики

Пример "увеличить счетчик, если не больше лимита":

```lua
local current = redis.call("GET", KEYS[1])
if not current then
  redis.call("SET", KEYS[1], 1, "EX", ARGV[2])
  return 1
end
current = tonumber(current)
if current >= tonumber(ARGV[1]) then
  return -1
end
redis.call("INCR", KEYS[1])
return current + 1
```

Запуск из Python:

```python
script = """
-- Lua script ...
"""
result = await redis_client.eval(script, 1, "rate:key", 100, 60)
```

Lua полезен, когда нужно несколько шагов "вместе" без гонок.

---

## 15. Пайплайны и производительность

Если много мелких операций, используй pipeline:

```python
pipe = redis_client.pipeline()
for i in range(1000):
    pipe.set(f"k:{i}", i)
await pipe.execute()
```

Почему быстрее:

- меньше сетевых round-trip между приложением и Redis.

Анти-паттерн:

- 1000 отдельных `await redis.set(...)` в цикле.

---

## 16. Persistence: RDB и AOF

Redis in-memory, но есть варианты сохранения на диск.

### RDB snapshots

- периодические снимки;
- быстро читать, меньше размер;
- риск потери последних секунд данных.

### AOF (append only file)

- запись каждой операции;
- выше durability;
- больше нагрузка/размер.

Часто для прод используют:

- `appendonly yes` + `appendfsync everysec`.

---

## 17. Redis в Docker Compose

Базовый практичный compose:

```yaml
services:
  redis:
    image: redis:7-alpine
    container_name: api-weather-redis
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

Подключение из `api` контейнера:

```text
redis://:your_password@redis:6379/0
```

`redis` - это имя сервиса в compose.

---

## 18. Настройки для production

Минимальный checklist:

1. Пароль/ACL включены (не открытый Redis).
2. Нет лишнего `ports` наружу, если доступ только из внутренней сети.
3. Включен persistence по требованиям (AOF/RDB).
4. Настроен memory limit и eviction policy.
5. Есть мониторинг (`INFO`, latency, keyspace hits/misses).

Полезные параметры:

- `maxmemory 512mb`
- `maxmemory-policy allkeys-lru` (для чистого кэша)

Пример в `redis.conf`:

```conf
maxmemory 512mb
maxmemory-policy allkeys-lru
appendonly yes
appendfsync everysec
```

---

## 19. Типичные ошибки

1. **Хранить большие JSON без сжатия и без лимитов**
   - RAM быстро заканчивается.

2. **Нет TTL у кэша**
   - ключи копятся бесконечно.

3. **Использовать Redis как "вечную БД"**
   - риск потери данных, сложнее восстановление.

4. **`KEYS *` в production**
   - блокирует сервер на больших объемах.
   - вместо этого `SCAN`.

5. **Нет namespace в ключах**
   - коллизии и хаос при отладке.

6. **Смешивать кэш и очередь в одном инстансе без лимитов**
   - queue может "съесть" память кэша или наоборот.

7. **Забывать закрывать async соединение при shutdown**
   - висящие подключения, грязное завершение.

---

## 20. Быстрая шпаргалка

### 20.1 Полезные команды redis-cli

```bash
redis-cli -a "$REDIS_PASSWORD" PING
redis-cli -a "$REDIS_PASSWORD" INFO memory
redis-cli -a "$REDIS_PASSWORD" INFO stats
redis-cli -a "$REDIS_PASSWORD" TTL cache:weather:moscow
redis-cli -a "$REDIS_PASSWORD" SCAN 0 MATCH cache:* COUNT 100
```

### 20.2 Базовый код-паттерн для кэша

```python
cached = await redis.get(key)
if cached:
    return decode(cached)

value = await load_from_source()
await redis.set(key, encode(value), ex=ttl)
return value
```

### 20.3 Рекомендуемые ключи

- `cache:*` - кэш данных
- `rate:*` - лимиты
- `lock:*` - блокировки
- `stream:*` - очереди Streams
- `session:*` - сессии/токены

### 20.4 Что выбрать для задач

- только кэш -> Redis String/Hash + TTL;
- надежная очередь -> Streams / RabbitMQ / Kafka;
- realtime push "online only" -> Pub/Sub;
- scheduler + async jobs в Python -> Celery + Redis/RabbitMQ.

---

Если хочешь, следующим шагом могу сделать отдельный файл
`theory/Redis_patterns_for_fastapi.md` именно под твой проект:

- кэш погоды по городу (cache-aside),
- rate limit на `POST /cities`,
- lock на фоновый refresh,
- stream-очередь для обновлений погоды воркером.
