# HTTPX — Полный конспект

> Справочник для быстрого поиска: открыл → нашёл → применил.

---

## Содержание

1. [Что такое httpx и зачем он](#1-что-такое-httpx-и-зачем-он)
2. [Установка](#2-установка)
3. [Sync-клиент](#3-sync-клиент)
4. [Async-клиент](#4-async-клиент)
5. [Все виды HTTP-запросов](#5-все-виды-http-запросов)
6. [Query params](#6-query-params)
7. [Headers](#7-headers)
8. [JSON body и form-данные](#8-json-body-и-form-данные)
9. [Ответ Response — что внутри](#9-ответ-response--что-внутри)
10. [Timeout — настройка таймаутов](#10-timeout--настройка-таймаутов)
11. [Обработка ошибок — исключения](#11-обработка-ошибок--исключения)
12. [Аутентификация](#12-аутентификация)
13. [Переиспользуемый клиент (connection pool)](#13-переиспользуемый-клиент-connection-pool)
14. [Интеграция с FastAPI lifespan](#14-интеграция-с-fastapi-lifespan)
15. [Тестирование — MockTransport и respx](#15-тестирование--mocktransport-и-respx)
16. [Retry — повторные попытки](#16-retry--повторные-попытки)
17. [Логирование запросов](#17-логирование-запросов)
18. [Streaming — потоковые ответы](#18-streaming--потоковые-ответы)
19. [Загрузка файлов](#19-загрузка-файлов)
20. [Иерархия исключений — шпаргалка](#20-иерархия-исключений--шпаргалка)
21. [Частые ошибки](#21-частые-ошибки)
22. [Быстрая шпаргалка](#22-быстрая-шпаргалка)

---

## 1. Что такое httpx и зачем он

`httpx` — современная HTTP-библиотека для Python.

| Фича | `requests` | `httpx` |
|---|---|---|
| Sync API | ✅ | ✅ |
| Async API | ❌ | ✅ |
| HTTP/2 | ❌ | ✅ (опционально) |
| Type hints | частично | полностью |
| Совместимость с FastAPI/asyncio | плохо | отлично |

**Когда использовать httpx:**
- Пишешь async-код (FastAPI, aiohttp, asyncio) → `httpx.AsyncClient`
- Пишешь sync-скрипты → `httpx.Client`
- Нужно тестировать HTTP-запросы без реального сервера → `MockTransport` / `respx`

---

## 2. Установка

```bash
pip install httpx

# С поддержкой HTTP/2
pip install httpx[http2]
```

---

## 3. Sync-клиент

Используй когда нет async (скрипты, CLI, Django views и т.п.).

### 3.1 Разовый запрос без клиента

```python
import httpx

resp = httpx.get("https://httpbin.org/get", params={"q": "python"})
resp.raise_for_status()
data = resp.json()
print(data)
```

**Разбор:**
- `httpx.get(...)` — создаёт временный клиент, делает запрос и закрывает его
- `raise_for_status()` — бросает исключение если статус 4xx или 5xx
- `resp.json()` — десериализует JSON в dict/list

### 3.2 Клиент как контекстный менеджер (рекомендуется)

```python
import httpx

with httpx.Client(timeout=10.0) as client:
    resp = client.get("https://httpbin.org/get")
    resp.raise_for_status()
    print(resp.status_code)   # 200
    print(resp.json())
```

**Разбор:**
- `with httpx.Client(...) as client:` — создаёт клиент с пулом соединений
- При выходе из блока `with` — соединения закрываются корректно
- Один клиент можно переиспользовать для многих запросов внутри блока

### 3.3 Базовый URL

```python
with httpx.Client(base_url="https://api.example.com") as client:
    resp = client.get("/users")          # GET https://api.example.com/users
    resp2 = client.get("/users/42")      # GET https://api.example.com/users/42
```

**Разбор:**
- `base_url` — prefixed к каждому запросу автоматически
- Полезно когда все запросы идут на один хост

---

## 4. Async-клиент

Используй в FastAPI, asyncio, любом async-коде.

### 4.1 Базовый async-запрос

```python
import httpx
import asyncio

async def main():
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get("https://httpbin.org/get")
        resp.raise_for_status()
        data = resp.json()
        print(data)

asyncio.run(main())
```

**Разбор:**
- `async with` — асинхронный контекстный менеджер
- `await client.get(...)` — `await` обязателен, без него получишь coroutine, а не Response
- `raise_for_status()` — sync-метод (не нужен await)
- `resp.json()` — тоже sync (парсинг уже готового тела)

### 4.2 Несколько запросов параллельно

```python
import httpx
import asyncio

async def fetch(client: httpx.AsyncClient, url: str) -> dict:
    resp = await client.get(url)
    resp.raise_for_status()
    return resp.json()

async def main():
    urls = [
        "https://httpbin.org/get?n=1",
        "https://httpbin.org/get?n=2",
        "https://httpbin.org/get?n=3",
    ]
    async with httpx.AsyncClient(timeout=10.0) as client:
        results = await asyncio.gather(*[fetch(client, url) for url in urls])
    print(results)

asyncio.run(main())
```

**Разбор:**
- `asyncio.gather(...)` — запускает все корутины параллельно
- Один клиент передаётся во все вызовы — соединения переиспользуются
- Это в разы быстрее чем делать запросы последовательно

---

## 5. Все виды HTTP-запросов

```python
async with httpx.AsyncClient() as client:

    # GET
    resp = await client.get("https://api.example.com/items")

    # POST
    resp = await client.post("https://api.example.com/items", json={"name": "apple"})

    # PUT — полная замена ресурса
    resp = await client.put("https://api.example.com/items/1", json={"name": "banana"})

    # PATCH — частичное обновление
    resp = await client.patch("https://api.example.com/items/1", json={"name": "cherry"})

    # DELETE
    resp = await client.delete("https://api.example.com/items/1")

    # HEAD — только заголовки, без тела
    resp = await client.head("https://api.example.com/items")

    # OPTIONS
    resp = await client.options("https://api.example.com/items")
```

---

## 6. Query params

Query params — это параметры в URL после `?` (`?q=python&limit=10`).

### 6.1 Передача через словарь

```python
params = {
    "q": "Moscow",
    "limit": 1,
    "appid": "my_api_key",
}

resp = await client.get("https://api.openweathermap.org/geo/1.0/direct", params=params)
# Итоговый URL: .../geo/1.0/direct?q=Moscow&limit=1&appid=my_api_key
```

### 6.2 Список значений для одного ключа

```python
params = {"tags": ["python", "httpx", "async"]}
resp = await client.get("https://api.example.com/search", params=params)
# URL: /search?tags=python&tags=httpx&tags=async
```

### 6.3 Проверка итогового URL

```python
req = client.build_request("GET", "/search", params={"q": "test"})
print(req.url)   # https://api.example.com/search?q=test
```

---

## 7. Headers

### 7.1 Заголовки на уровне клиента (применяются ко всем запросам)

```python
client = httpx.AsyncClient(
    base_url="https://api.example.com",
    headers={
        "Authorization": "Bearer MY_TOKEN",
        "Accept": "application/json",
        "User-Agent": "MyApp/1.0",
    }
)
```

### 7.2 Заголовки на уровне запроса (дополняют/перекрывают клиентские)

```python
resp = await client.get("/data", headers={"X-Request-ID": "abc123"})
```

### 7.3 Чтение заголовков ответа

```python
resp = await client.get("https://api.example.com/data")
print(resp.headers["content-type"])          # application/json
print(resp.headers.get("x-ratelimit-remaining"))  # None если нет
```

**Важно:** заголовки в httpx регистронезависимы (`Content-Type` == `content-type`).

---

## 8. JSON body и form-данные

### 8.1 POST с JSON

```python
payload = {
    "username": "john",
    "email": "john@example.com",
    "age": 30,
}

resp = await client.post("https://api.example.com/users", json=payload)
# httpx автоматически:
#   - сериализует dict в JSON-строку
#   - ставит Content-Type: application/json
resp.raise_for_status()
created_user = resp.json()
print(created_user["id"])
```

### 8.2 POST с form-данными (application/x-www-form-urlencoded)

```python
resp = await client.post(
    "https://api.example.com/login",
    data={"username": "john", "password": "secret"},
)
# Content-Type: application/x-www-form-urlencoded
```

### 8.3 POST с multipart/form-data (загрузка файла)

```python
with open("photo.jpg", "rb") as f:
    resp = await client.post(
        "https://api.example.com/upload",
        files={"photo": ("photo.jpg", f, "image/jpeg")},
        data={"description": "My photo"},
    )
```

**Разбор:**
- `json=` → Content-Type: application/json, тело сериализуется автоматически
- `data=` → Content-Type: application/x-www-form-urlencoded (как HTML форма)
- `files=` → Content-Type: multipart/form-data (файлы + поля формы)

---

## 9. Ответ Response — что внутри

```python
resp = await client.get("https://httpbin.org/get")

resp.status_code          # int: 200, 404, 500...
resp.text                 # str: тело ответа как строка
resp.content              # bytes: тело ответа как байты
resp.json()               # dict/list: распарсить JSON
resp.headers              # Headers: заголовки ответа
resp.url                  # URL: финальный URL (после редиректов)
resp.request              # Request: оригинальный запрос
resp.elapsed              # timedelta: время выполнения
resp.encoding             # str: кодировка ('utf-8' и т.п.)
resp.is_success           # bool: True если 2xx
resp.is_error             # bool: True если 4xx/5xx
resp.is_redirect          # bool: True если 3xx
```

### Пример с разбором ответа

```python
resp = await client.get("https://api.example.com/users/42")

if resp.status_code == 200:
    user = resp.json()
    print(f"Имя: {user['name']}")
    print(f"Время запроса: {resp.elapsed.total_seconds():.2f}s")
elif resp.status_code == 404:
    print("Пользователь не найден")
else:
    print(f"Ошибка: {resp.status_code}")
    print(resp.text)
```

---

## 10. Timeout — настройка таймаутов

Таймаут — максимальное время ожидания. Без него запрос может висеть бесконечно.

### 10.1 Простой таймаут (одно число)

```python
async with httpx.AsyncClient(timeout=10.0) as client:
    resp = await client.get("https://api.example.com/data")
# Применяется ко всем фазам: connect + read + write + pool
```

### 10.2 Детальный таймаут

```python
timeout = httpx.Timeout(
    connect=3.0,   # сколько ждать установки TCP-соединения
    read=10.0,     # сколько ждать ответа от сервера
    write=5.0,     # сколько ждать отправки запроса
    pool=2.0,      # сколько ждать свободного соединения из пула
)

async with httpx.AsyncClient(timeout=timeout) as client:
    resp = await client.get("https://api.example.com/data")
```

### 10.3 Отдельный таймаут на запрос

```python
async with httpx.AsyncClient(timeout=10.0) as client:
    # Этот запрос имеет свой таймаут, перекрывает клиентский
    resp = await client.get("/slow-endpoint", timeout=30.0)

    # Отключить таймаут для конкретного запроса
    resp2 = await client.get("/very-slow", timeout=None)
```

### 10.4 Перехват таймаут-ошибки

```python
try:
    resp = await client.get("https://api.example.com/data", timeout=5.0)
except httpx.TimeoutException:
    print("Запрос превысил таймаут")
except httpx.ConnectTimeout:
    print("Не удалось установить соединение за отведённое время")
except httpx.ReadTimeout:
    print("Сервер не ответил за отведённое время")
```

---

## 11. Обработка ошибок — исключения

### 11.1 raise_for_status()

```python
resp = await client.get("https://api.example.com/data")
resp.raise_for_status()   # бросает HTTPStatusError если статус 4xx или 5xx
```

### 11.2 Полный блок обработки

```python
import httpx

try:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get("https://api.example.com/data", params={"q": "test"})
        resp.raise_for_status()
        data = resp.json()

except httpx.ConnectTimeout:
    # Не удалось подключиться за timeout секунд
    raise RuntimeError("Сервер недоступен: timeout при подключении")

except httpx.ReadTimeout:
    # Сервер подключился, но не прислал ответ вовремя
    raise RuntimeError("Сервер не ответил вовремя")

except httpx.TimeoutException:
    # Любой другой тип таймаута
    raise RuntimeError("Timeout при запросе")

except httpx.HTTPStatusError as e:
    # raise_for_status() поймал 4xx/5xx
    status = e.response.status_code
    if status == 401:
        raise RuntimeError("Неверный API-ключ (401)")
    elif status == 403:
        raise RuntimeError("Нет доступа (403)")
    elif status == 404:
        raise RuntimeError("Ресурс не найден (404)")
    elif status == 429:
        raise RuntimeError("Превышен лимит запросов (429)")
    elif status >= 500:
        raise RuntimeError(f"Ошибка сервера ({status})")
    else:
        raise RuntimeError(f"HTTP ошибка: {status}")

except httpx.RequestError as e:
    # Любая сетевая ошибка (DNS, соединение, SSL...)
    raise RuntimeError(f"Сетевая ошибка: {e}")
```

### 11.3 Получить тело ошибки

```python
except httpx.HTTPStatusError as e:
    print(e.response.status_code)   # 422
    print(e.response.text)          # {"detail": "Validation error"}
    print(e.response.json())        # {"detail": "Validation error"}
    print(e.request.url)            # URL запроса
```

---

## 12. Аутентификация

### 12.1 HTTP Basic Auth

```python
async with httpx.AsyncClient(auth=("username", "password")) as client:
    resp = await client.get("https://api.example.com/private")
```

### 12.2 Bearer Token (через заголовок)

```python
async with httpx.AsyncClient(
    headers={"Authorization": f"Bearer {access_token}"}
) as client:
    resp = await client.get("https://api.example.com/private")
```

### 12.3 API Key через query param

```python
async with httpx.AsyncClient() as client:
    resp = await client.get(
        "https://api.openweathermap.org/data/2.5/weather",
        params={"appid": settings.OWM_API_KEY, "q": "Moscow"}
    )
```

### 12.4 Кастомный класс Auth

```python
class TokenAuth(httpx.Auth):
    def __init__(self, token: str):
        self.token = token

    def auth_flow(self, request):
        request.headers["Authorization"] = f"Bearer {self.token}"
        yield request

async with httpx.AsyncClient(auth=TokenAuth("my_secret_token")) as client:
    resp = await client.get("https://api.example.com/private")
```

**Разбор:**
- `auth_flow` — генератор: ты модифицируешь запрос и отдаёшь его с `yield`
- После `yield` можешь получить ответ и при необходимости повторить запрос (например при 401)

---

## 13. Переиспользуемый клиент (connection pool)

### Проблема с клиентом "на каждый запрос"

```python
# ❌ Плохо — каждый вызов создаёт и закрывает клиент
async def get_user(user_id: int) -> dict:
    async with httpx.AsyncClient() as client:   # новое TCP соединение
        resp = await client.get(f"/users/{user_id}")
        return resp.json()
# При 100 запросах = 100 раз открыть/закрыть соединение
```

### Решение — один клиент на всё приложение

```python
# ✅ Хорошо — один клиент, пул соединений переиспользуется
class ApiClient:
    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    async def start(self):
        self._client = httpx.AsyncClient(
            base_url="https://api.example.com",
            timeout=10.0,
            headers={"Authorization": "Bearer TOKEN"},
        )

    async def stop(self):
        if self._client:
            await self._client.aclose()

    async def get_user(self, user_id: int) -> dict:
        resp = await self._client.get(f"/users/{user_id}")
        resp.raise_for_status()
        return resp.json()
```

**Разбор:**
- `aclose()` — асинхронное закрытие клиента (используй для AsyncClient)
- `close()` — синхронное закрытие (для Client)
- Один экземпляр клиента держит пул TCP-соединений → быстрее

---

## 14. Интеграция с FastAPI lifespan

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
import httpx

# Глобальный клиент
http_client: httpx.AsyncClient | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: создаём клиент один раз
    global http_client
    http_client = httpx.AsyncClient(
        base_url="https://api.openweathermap.org",
        timeout=httpx.Timeout(connect=3.0, read=10.0),
        headers={"Accept": "application/json"},
    )
    print("HTTP client started")

    yield  # приложение работает

    # Shutdown: закрываем клиент корректно
    await http_client.aclose()
    print("HTTP client closed")

app = FastAPI(lifespan=lifespan)

@app.get("/weather")
async def get_weather(city: str):
    resp = await http_client.get(
        "/data/2.5/weather",
        params={"q": city, "appid": "KEY", "units": "metric"},
    )
    resp.raise_for_status()
    return resp.json()
```

**Разбор:**
- `lifespan` — контекстный менеджер, код до `yield` = startup, после = shutdown
- Клиент создаётся один раз при старте и закрывается при остановке приложения
- Все роуты используют один клиент с пулом соединений

### Вариант через зависимость (Dependency Injection)

```python
from fastapi import Depends

async def get_http_client() -> httpx.AsyncClient:
    return http_client  # возвращаем глобальный клиент

@app.get("/weather")
async def get_weather(
    city: str,
    client: httpx.AsyncClient = Depends(get_http_client),
):
    resp = await client.get("/data/2.5/weather", params={"q": city, "appid": "KEY"})
    resp.raise_for_status()
    return resp.json()
```

---

## 15. Тестирование — MockTransport и respx

### 15.1 httpx.MockTransport — встроенный мок

```python
import httpx
import pytest

def mock_handler(request: httpx.Request) -> httpx.Response:
    """Обработчик вместо реального сервера"""
    if request.url.path == "/geo/1.0/direct":
        return httpx.Response(
            status_code=200,
            json=[{"lat": 55.75, "lon": 37.61, "name": "Moscow"}],
        )
    return httpx.Response(status_code=404, json={"error": "not found"})

@pytest.mark.asyncio
async def test_geocode():
    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        resp = await client.get("https://api.openweathermap.org/geo/1.0/direct",
                                 params={"q": "Moscow"})
        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["lat"] == 55.75
```

**Разбор:**
- `MockTransport(handler)` — подменяет реальный транспорт (TCP) на функцию
- Реальные HTTP-запросы не отправляются
- `mock_handler` получает `Request` и возвращает `Response`

### 15.2 Мок различных сценариев

```python
def make_handler(status: int, body=None):
    """Фабрика обработчиков для разных статусов"""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=status, json=body or {})
    return handler

# Успешный ответ
@pytest.mark.asyncio
async def test_success():
    transport = httpx.MockTransport(
        make_handler(200, [{"lat": 55.75, "lon": 37.61}])
    )
    async with httpx.AsyncClient(transport=transport) as client:
        resp = await client.get("https://example.com/geo")
        assert resp.status_code == 200

# 401 Unauthorized
@pytest.mark.asyncio
async def test_unauthorized():
    transport = httpx.MockTransport(make_handler(401, {"error": "invalid key"}))
    async with httpx.AsyncClient(transport=transport) as client:
        resp = await client.get("https://example.com/geo")
        with pytest.raises(httpx.HTTPStatusError):
            resp.raise_for_status()

# Пустой ответ (город не найден)
@pytest.mark.asyncio
async def test_city_not_found():
    transport = httpx.MockTransport(make_handler(200, []))  # пустой список
    async with httpx.AsyncClient(transport=transport) as client:
        resp = await client.get("https://example.com/geo")
        data = resp.json()
        assert data == []

# Таймаут
@pytest.mark.asyncio
async def test_timeout():
    def timeout_handler(request):
        raise httpx.ReadTimeout("Read timeout", request=request)

    transport = httpx.MockTransport(timeout_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(httpx.ReadTimeout):
            await client.get("https://example.com/geo")
```

### 15.3 respx — более удобный мок (сторонняя библиотека)

```bash
pip install respx
```

```python
import httpx
import respx
import pytest

@pytest.mark.asyncio
@respx.mock
async def test_with_respx():
    # Регистрируем маршрут
    respx.get("https://api.openweathermap.org/geo/1.0/direct").mock(
        return_value=httpx.Response(200, json=[{"lat": 55.75, "lon": 37.61}])
    )

    async with httpx.AsyncClient() as client:
        resp = await client.get("https://api.openweathermap.org/geo/1.0/direct")
        assert resp.status_code == 200
        assert resp.json()[0]["lat"] == 55.75
```

---

## 16. Retry — повторные попытки

### 16.1 Ручной retry через цикл

```python
import asyncio
import httpx

async def get_with_retry(
    client: httpx.AsyncClient,
    url: str,
    params: dict,
    max_retries: int = 3,
    delay: float = 1.0,
) -> httpx.Response:
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp

        except httpx.TimeoutException as e:
            last_error = e
            print(f"Attempt {attempt}/{max_retries}: timeout, retry in {delay}s")
            await asyncio.sleep(delay)

        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status >= 500:
                # 5xx — повторяем
                last_error = e
                print(f"Attempt {attempt}/{max_retries}: server error {status}, retry")
                await asyncio.sleep(delay)
            else:
                # 4xx — не повторяем, сразу кидаем
                raise

    raise RuntimeError(f"All {max_retries} attempts failed") from last_error
```

### 16.2 Retry через tenacity

```bash
pip install tenacity
```

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx

@retry(
    stop=stop_after_attempt(3),                          # максимум 3 попытки
    wait=wait_exponential(multiplier=1, min=1, max=10),  # экспоненциальная задержка: 1s, 2s, 4s...
    retry=retry_if_exception_type((
        httpx.TimeoutException,
        httpx.ConnectError,
    )),
)
async def fetch_with_retry(client: httpx.AsyncClient, url: str) -> dict:
    resp = await client.get(url)
    resp.raise_for_status()
    return resp.json()
```

**Разбор:**
- `stop_after_attempt(3)` — не более 3 попыток
- `wait_exponential(...)` — пауза между попытками: 1s → 2s → 4s
- `retry_if_exception_type(...)` — повторять только при этих исключениях
- При 4xx tenacity не перехватывает — запрос упадёт сразу (это правильно)

---

## 17. Логирование запросов

### 17.1 Через event hooks

```python
import httpx
import logging
import time

logger = logging.getLogger(__name__)

async def log_request(request: httpx.Request):
    logger.info(f"→ {request.method} {request.url}")

async def log_response(response: httpx.Response):
    # elapsed доступен только после того как ответ получен
    await response.aread()  # если streaming — считать тело
    logger.info(
        f"← {response.status_code} {response.url} "
        f"({response.elapsed.total_seconds():.2f}s)"
    )

async with httpx.AsyncClient(
    event_hooks={
        "request": [log_request],
        "response": [log_response],
    }
) as client:
    resp = await client.get("https://api.example.com/data")
```

### 17.2 Логирование с измерением времени

```python
import time

async def log_request(request: httpx.Request):
    request.extensions["timer_start"] = time.monotonic()
    # Не логируем headers — там может быть API-ключ!
    logger.info(f"REQUEST: {request.method} {request.url.path}")

async def log_response(response: httpx.Response):
    start = response.request.extensions.get("timer_start", time.monotonic())
    elapsed = time.monotonic() - start
    logger.info(
        f"RESPONSE: {response.status_code} | "
        f"{response.request.method} {response.request.url.path} | "
        f"{elapsed:.3f}s"
    )
```

**Важно:** никогда не логируй `Authorization` заголовки и API-ключи из params.

---

## 18. Streaming — потоковые ответы

Используй когда ответ большой (файлы, длинный JSON) и не хочешь держать всё в памяти.

### 18.1 Потоковое чтение по чанкам

```python
async with httpx.AsyncClient() as client:
    async with client.stream("GET", "https://example.com/large-file.zip") as resp:
        resp.raise_for_status()
        with open("large-file.zip", "wb") as f:
            async for chunk in resp.aiter_bytes(chunk_size=8192):
                f.write(chunk)
```

**Разбор:**
- `client.stream(...)` — не скачивает тело сразу
- `resp.aiter_bytes(chunk_size=8192)` — читает по 8KB за раз
- При выходе из `async with` — соединение закрывается

### 18.2 Потоковое чтение текста

```python
async with client.stream("GET", "https://example.com/large.txt") as resp:
    async for line in resp.aiter_lines():
        print(line)
```

---

## 19. Загрузка файлов

### 19.1 Загрузка одного файла

```python
async with httpx.AsyncClient() as client:
    with open("report.pdf", "rb") as f:
        resp = await client.post(
            "https://api.example.com/upload",
            files={"file": ("report.pdf", f, "application/pdf")},
        )
    resp.raise_for_status()
    print(resp.json())   # {"url": "https://cdn.example.com/report.pdf"}
```

### 19.2 Загрузка файла + дополнительные поля

```python
async with httpx.AsyncClient() as client:
    with open("avatar.jpg", "rb") as f:
        resp = await client.post(
            "https://api.example.com/profile/avatar",
            files={"avatar": ("avatar.jpg", f, "image/jpeg")},
            data={"user_id": "42", "description": "Profile photo"},
        )
```

---

## 20. Иерархия исключений — шпаргалка

```
httpx.HTTPError
├── httpx.RequestError              # Ошибки при отправке запроса
│   ├── httpx.TransportError
│   │   ├── httpx.TimeoutException  # Любой таймаут
│   │   │   ├── httpx.ConnectTimeout    # Таймаут при подключении
│   │   │   ├── httpx.ReadTimeout       # Таймаут при чтении ответа
│   │   │   ├── httpx.WriteTimeout      # Таймаут при отправке
│   │   │   └── httpx.PoolTimeout       # Таймаут ожидания пула
│   │   └── httpx.ConnectError      # Не удалось подключиться (DNS, refused...)
│   └── httpx.InvalidURL           # Неверный URL
└── httpx.HTTPStatusError          # 4xx/5xx (только после raise_for_status())
```

**Практический вывод:**
- Ловишь **все** сетевые проблемы → `except httpx.RequestError`
- Ловишь **только таймауты** → `except httpx.TimeoutException`
- Ловишь **HTTP ошибки** → `except httpx.HTTPStatusError`

---

## 21. Частые ошибки

| Ошибка | Почему | Как исправить |
|---|---|---|
| `coroutine was never awaited` | Забыл `await client.get(...)` | Добавь `await` |
| `AttributeError: 'coroutine' object has no attribute 'json'` | Та же причина — нет `await` | Добавь `await` |
| `RuntimeError: Event loop is closed` | `AsyncClient` не закрыт, используется после завершения | Всегда используй `async with` или вызывай `aclose()` |
| `TypeError: tuple() takes at most 1 argument` | `tuple(a, b)` — неверный синтаксис | Используй `(a, b)` или `tuple([a, b])` |
| `KeyError: 'lat'` | `data[0]` без проверки `if not data` | Сначала `if not data: raise ...` |
| `httpx.HTTPStatusError` не поймал ошибку | Забыл вызвать `raise_for_status()` | Добавь `resp.raise_for_status()` |
| `appid` получает URL вместо ключа | Перепутал переменные | `"appid": settings.OWM_API_KEY` |
| Используешь sync `httpx.Client` в async | `BlockingIOError` или зависание | Используй `httpx.AsyncClient` |

---

## 22. Быстрая шпаргалка

### Минимальный async-запрос

```python
import httpx

async with httpx.AsyncClient(timeout=10.0) as client:
    resp = await client.get("https://api.example.com/data", params={"q": "test"})
    resp.raise_for_status()
    data = resp.json()
```

### POST с JSON

```python
async with httpx.AsyncClient() as client:
    resp = await client.post("https://api.example.com/items", json={"name": "test"})
    resp.raise_for_status()
    result = resp.json()
```

### Полный блок try/except

```python
try:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()
except httpx.TimeoutException:
    raise RuntimeError("Timeout")
except httpx.HTTPStatusError as e:
    raise RuntimeError(f"HTTP {e.response.status_code}")
except httpx.RequestError as e:
    raise RuntimeError(f"Network error: {e}")
```

### Детальный таймаут

```python
timeout = httpx.Timeout(connect=3.0, read=10.0, write=5.0, pool=2.0)
async with httpx.AsyncClient(timeout=timeout) as client:
    ...
```

### Клиент с базовым URL и заголовками

```python
async with httpx.AsyncClient(
    base_url="https://api.example.com",
    timeout=10.0,
    headers={"Authorization": "Bearer TOKEN", "Accept": "application/json"},
) as client:
    resp = await client.get("/users")
```

### Проверка ответа

```python
resp.status_code      # 200
resp.json()           # dict/list
resp.text             # str
resp.content          # bytes
resp.headers          # Headers
resp.elapsed          # timedelta
resp.is_success       # bool
```

### Иерархия исключений (быстро)

```python
httpx.TimeoutException    # таймаут
httpx.ConnectError        # нет соединения
httpx.HTTPStatusError     # 4xx/5xx (нужен raise_for_status)
httpx.RequestError        # родитель всех сетевых ошибок
```

---

## Ссылки

- [Документация httpx](https://www.python-httpx.org/)
- [Quickstart](https://www.python-httpx.org/quickstart/)
- [Async Support](https://www.python-httpx.org/async/)
- [Exceptions](https://www.python-httpx.org/exceptions/)
- [Advanced Usage](https://www.python-httpx.org/advanced/)
- [respx (мок-библиотека)](https://lundberg.github.io/respx/)
- [tenacity (retry)](https://tenacity.readthedocs.io/)
