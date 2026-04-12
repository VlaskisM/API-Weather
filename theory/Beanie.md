# MongoDB — Полный конспект (PyMongo + Motor + Beanie)

> Справочник для быстрого поиска: открыл → нашёл → применил.
> Акцент на асинхронный стек: **Motor** (async-драйвер) + **Beanie** (ODM).

---

## Содержание

1. [MongoDB в двух словах](#1-mongodb-в-двух-словах)
2. [Установка](#2-установка)
3. [PyMongo — синхронный драйвер](#3-pymongo--синхронный-драйвер)
4. [Motor — асинхронный драйвер](#4-motor--асинхронный-драйвер)
5. [Beanie — ODM для async](#5-beanie--odm-для-async)
6. [Модели Beanie — Document](#6-модели-beanie--document)
7. [Индексы в Beanie](#7-индексы-в-beanie)
8. [CRUD через Beanie](#8-crud-через-beanie)
9. [Фильтры и операторы запросов](#9-фильтры-и-операторы-запросов)
10. [Update — обновление документов](#10-update--обновление-документов)
11. [Aggregation Pipeline](#11-aggregation-pipeline)
12. [Связи между документами — Link и BackLink](#12-связи-между-документами--link-и-backlink)
13. [Инициализация в FastAPI lifespan](#13-инициализация-в-fastapi-lifespan)
14. [Репозиторий — паттерн доступа к данным](#14-репозиторий--паттерн-доступа-к-данным)
15. [Тестирование с mongomock / mongomock-motor](#15-тестирование-с-mongomock--mongomock-motor)
16. [Docker — MongoDB для разработки](#16-docker--mongodb-для-разработки)
17. [Частые ошибки](#17-частые-ошибки)
18. [Быстрая шпаргалка](#18-быстрая-шпаргалка)

---

## 1. MongoDB в двух словах

MongoDB — документоориентированная БД. Данные хранятся в **коллекциях** как **документы** (BSON — JSON + дополнительные типы).

| SQL концепция | MongoDB аналог |
|---|---|
| База данных | База данных |
| Таблица | Коллекция (Collection) |
| Строка | Документ (Document) |
| Колонка | Поле (Field) |
| PRIMARY KEY | `_id` (ObjectId по умолчанию) |
| JOIN | `$lookup` в aggregation или вложенные документы |
| INDEX | INDEX (аналогично) |

**Ключевые особенности:**
- Документ = JSON-подобная структура (гибкая схема)
- Лимит размера документа — **16 МБ**
- `_id` — уникальный идентификатор, по умолчанию `ObjectId` (12 байт)
- Нет JOIN из коробки — данные либо вкладываются, либо связываются через `_id`
- Транзакции требуют **replica set**

**Три уровня абстракции в Python:**

```
PyMongo (sync)   — низкий уровень, словари, синхронный
Motor            — async обёртка над PyMongo, те же методы + await
Beanie           — ODM поверх Motor, Pydantic-модели + await
```

---

## 2. Установка

```bash
# Только PyMongo (sync)
pip install pymongo

# Motor — async драйвер (включает PyMongo)
pip install motor

# Beanie ODM (включает motor)
pip install beanie
```

---

## 3. PyMongo — синхронный драйвер

Используй для скриптов, CLI, Django. В FastAPI (async) — не подходит.

### 3.1 Подключение

```python
from pymongo import MongoClient

# Простое подключение
client = MongoClient("mongodb://localhost:27017")

# С аутентификацией
client = MongoClient("mongodb://root:secret@localhost:27017/?authSource=admin")

# Получение базы и коллекции
db = client["my_database"]
users = db["users"]

# Проверка подключения
client.admin.command("ping")  # {"ok": 1.0} если всё ок
```

### 3.2 Иерархия объектов

```python
client = MongoClient(uri)        # 1 на весь процесс, держит пул соединений
db = client["my_db"]            # объект базы
collection = db["users"]        # объект коллекции
```

### 3.3 Insert

```python
# Вставка одного документа
result = users.insert_one({
    "name": "Alice",
    "email": "alice@example.com",
    "age": 28,
})
print(result.inserted_id)   # ObjectId('...')

# Вставка нескольких
result = users.insert_many([
    {"name": "Bob", "age": 30},
    {"name": "Charlie", "age": 25},
])
print(result.inserted_ids)  # [ObjectId(...), ObjectId(...)]
```

### 3.4 Find

```python
from bson import ObjectId

# Найти один
user = users.find_one({"name": "Alice"})
# → {"_id": ObjectId(...), "name": "Alice", "email": "..."}

# Найти по _id
user = users.find_one({"_id": ObjectId("64f1a2b3c4d5e6f7a8b9c0d1")})

# Найти несколько (возвращает Cursor)
cursor = users.find({"age": {"$gte": 18}})
for doc in cursor:
    print(doc["name"])

# Limit, skip, sort
cursor = (
    users
    .find({"age": {"$gte": 18}})
    .sort("name", 1)   # 1 = ASC, -1 = DESC
    .skip(10)
    .limit(5)
)

# Выбрать только нужные поля (projection)
cursor = users.find({}, {"name": 1, "email": 1, "_id": 0})
```

### 3.5 Update

```python
# Обновить одно поле
users.update_one(
    {"name": "Alice"},
    {"$set": {"age": 29}},
)

# Обновить несколько документов
users.update_many(
    {"age": {"$lt": 18}},
    {"$set": {"is_minor": True}},
)

# Upsert — обновить если есть, вставить если нет
users.update_one(
    {"email": "new@example.com"},
    {"$set": {"name": "New User", "age": 20}},
    upsert=True,
)

# Инкремент числового поля
users.update_one({"name": "Alice"}, {"$inc": {"age": 1}})

# Добавить элемент в массив
users.update_one({"name": "Alice"}, {"$push": {"tags": "admin"}})
```

### 3.6 Delete

```python
# Удалить один
users.delete_one({"name": "Alice"})

# Удалить несколько
users.delete_many({"age": {"$lt": 18}})
```

### 3.7 Индексы

```python
from pymongo import ASCENDING, DESCENDING

# Простой индекс
users.create_index([("email", ASCENDING)], unique=True)

# Составной индекс
users.create_index([("city", ASCENDING), ("age", DESCENDING)])

# TTL-индекс (документы удаляются через N секунд)
sessions.create_index("created_at", expireAfterSeconds=3600)

# Посмотреть индексы
print(list(users.index_information()))
```

---

## 4. Motor — асинхронный драйвер

Motor = async обёртка над PyMongo. API идентичен, но методы нужно `await`.

### 4.1 Подключение

```python
from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client["my_database"]
users = db["users"]

# Один клиент на всё приложение!
# Создавай при старте, закрывай при остановке: client.close()
```

### 4.2 Те же CRUD, но с await

```python
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

async def main():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["my_database"]
    users = db["users"]

    # Insert
    result = await users.insert_one({"name": "Alice", "age": 28})
    print(result.inserted_id)

    # Find one
    doc = await users.find_one({"name": "Alice"})
    print(doc)

    # Find many — cursor не awaitable, но to_list нужен await
    docs = await users.find({"age": {"$gte": 18}}).to_list(length=100)
    for doc in docs:
        print(doc["name"])

    # Update
    await users.update_one({"name": "Alice"}, {"$set": {"age": 29}})

    # Delete
    await users.delete_one({"name": "Alice"})

    client.close()

asyncio.run(main())
```

**Разбор:**
- `await users.insert_one(...)` — отправляет запрос асинхронно, не блокирует event loop
- `find(...)` возвращает `AsyncIOMotorCursor` — итерировать через `async for` или `.to_list()`
- `to_list(length=N)` — N это максимальное кол-во документов, загружаемых в память

### 4.3 Итерация по курсору

```python
# Вариант 1: async for (ленивый, не грузит всё в память сразу)
async for doc in users.find({"country": "RU"}):
    print(doc["name"])

# Вариант 2: to_list (загружает всё)
docs = await users.find({"country": "RU"}).to_list(length=1000)
```

---

## 5. Beanie — ODM для async

Beanie = Pydantic модели + Motor под капотом + удобный API запросов.

**Цепочка:** `Beanie → Motor → MongoDB`

**Почему Beanie а не чистый Motor:**
- Модели документов — это Pydantic-классы (валидация, типы, автодополнение)
- Индексы объявляются декларативно рядом с полями
- Запросы выглядят как `User.find(User.age >= 18)` вместо словарей
- Автоматическое создание коллекций и индексов при инициализации

### 5.1 Минимальный пример

```python
import asyncio
from beanie import Document, init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import EmailStr

class User(Document):
    name: str
    email: EmailStr
    age: int

    class Settings:
        name = "users"  # имя коллекции в MongoDB

async def main():
    # 1. Подключение
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["my_database"]

    # 2. Инициализация Beanie
    await init_beanie(database=db, document_models=[User])

    # 3. Создание документа
    user = User(name="Alice", email="alice@example.com", age=28)
    await user.insert()
    print(user.id)   # ObjectId

    # 4. Поиск
    found = await User.find_one(User.name == "Alice")
    print(found.email)

    # 5. Обновление
    found.age = 29
    await found.save()

    # 6. Удаление
    await found.delete()

asyncio.run(main())
```

---

## 6. Модели Beanie — Document

### 6.1 Структура модели

```python
from beanie import Document, Indexed, before_event, after_event, Insert, Update
from pydantic import Field, EmailStr
from datetime import datetime
from typing import Optional
from bson import ObjectId

class User(Document):
    # Поля — обычные Pydantic аннотации
    name: str
    email: EmailStr
    age: int = Field(ge=0, le=150)          # валидация Pydantic
    bio: Optional[str] = None
    is_active: bool = True
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"              # имя коллекции в MongoDB
        use_state_management = True # для .save_changes() — только изменённые поля

    class Config:
        # Позволяет использовать ObjectId как тип
        arbitrary_types_allowed = True
```

### 6.2 _id и id

```python
user = await User.find_one(User.name == "Alice")

user.id          # PydanticObjectId — то же самое что _id в MongoDB
str(user.id)     # "64f1a2b3c4d5e6f7a8b9c0d1"

# Поиск по id
from beanie import PydanticObjectId

user = await User.get("64f1a2b3c4d5e6f7a8b9c0d1")
# или
user = await User.find_one(User.id == PydanticObjectId("64f1a2b3c4d5e6f7a8b9c0d1"))
```

### 6.3 Хуки — before/after событий

```python
from beanie import before_event, after_event, Insert, Update, Delete

class User(Document):
    name: str
    password_hash: str
    updated_at: Optional[datetime] = None

    @before_event(Insert)
    def set_created(self):
        pass  # можно выставить поля перед вставкой

    @before_event(Update)
    def set_updated(self):
        self.updated_at = datetime.utcnow()

    @after_event(Delete)
    async def on_deleted(self):
        # например, удалить связанные файлы
        pass
```

---

## 7. Индексы в Beanie

### 7.1 Indexed — декларативный индекс на поле

```python
from beanie import Document, Indexed

class User(Document):
    email: Indexed(str, unique=True)   # уникальный индекс
    name: Indexed(str)                  # обычный индекс
    age: int                            # без индекса
    country: Indexed(str)               # индекс для поиска по стране
```

### 7.2 Составные и сложные индексы через Settings

```python
from beanie import Document
from pymongo import ASCENDING, DESCENDING, IndexModel

class Post(Document):
    title: str
    author_id: str
    created_at: datetime
    tags: list[str]

    class Settings:
        name = "posts"
        indexes = [
            # Составной индекс
            IndexModel(
                [("author_id", ASCENDING), ("created_at", DESCENDING)],
                name="author_date_idx",
            ),
            # Индекс по массиву (multikey)
            IndexModel([("tags", ASCENDING)], name="tags_idx"),
            # TTL индекс
            IndexModel(
                [("created_at", ASCENDING)],
                name="ttl_idx",
                expireAfterSeconds=86400,  # удалить через 24 часа
            ),
        ]
```

**Разбор:**
- `init_beanie(...)` автоматически создаёт все индексы из `Settings.indexes` и `Indexed(...)`
- TTL-индекс — MongoDB сам удаляет документы после истечения времени

---

## 8. CRUD через Beanie

### 8.1 Create — создание документов

```python
# Вариант 1: создать объект и вставить
user = User(name="Alice", email="alice@example.com", age=28)
await user.insert()
print(user.id)   # ObjectId установлен после вставки

# Вариант 2: create (shortcut)
user = await User.insert_one(User(name="Bob", email="bob@example.com", age=30))

# Вариант 3: массовая вставка
users = [
    User(name="Charlie", email="c@example.com", age=22),
    User(name="Diana", email="d@example.com", age=35),
]
await User.insert_many(users)
```

### 8.2 Read — поиск документов

```python
# Найти один (None если не найден)
user = await User.find_one(User.email == "alice@example.com")
if user is None:
    raise ValueError("User not found")

# Найти по id
user = await User.get("64f1a2b3c4d5e6f7a8b9c0d1")

# Найти все (возвращает FindMany → нужно to_list())
users = await User.find().to_list()

# Найти с фильтром
adult_users = await User.find(User.age >= 18).to_list()

# Несколько условий (AND)
active_adults = await User.find(
    User.age >= 18,
    User.is_active == True,
).to_list()

# Сортировка
users = await User.find().sort(+User.name).to_list()   # ASC
users = await User.find().sort(-User.age).to_list()    # DESC

# Limit и Skip (пагинация)
page = 2
per_page = 10
users = await User.find().skip((page - 1) * per_page).limit(per_page).to_list()

# Подсчёт
count = await User.find(User.is_active == True).count()

# Проверка существования
exists = await User.find_one(User.email == "alice@example.com") is not None
```

### 8.3 Update — обновление

```python
user = await User.find_one(User.name == "Alice")

# Вариант 1: изменить поля и save() (перезапишет весь документ)
user.age = 29
user.bio = "Updated bio"
await user.save()

# Вариант 2: save_changes() — только изменённые поля (нужен use_state_management=True)
user.age = 29
await user.save_changes()   # отправит только {"$set": {"age": 29}}

# Вариант 3: update() с оператором (без загрузки документа)
from beanie.odm.operators.update.general import Set, Inc, Push

await User.find(User.name == "Alice").update(
    Set({User.age: 29})
)

# Инкремент
await User.find(User.name == "Alice").update(
    Inc({User.age: 1})
)

# Добавить в массив
await User.find(User.name == "Alice").update(
    Push({User.tags: "admin"})
)

# Обновить несколько
await User.find(User.is_active == False).update(
    Set({User.is_active: True})
)

# Upsert через find().upsert()
await User.find(User.email == "new@example.com").upsert(
    Set({User.name: "New User"}),
    on_insert=User(name="New User", email="new@example.com", age=20),
)
```

### 8.4 Delete — удаление

```python
user = await User.find_one(User.name == "Alice")
await user.delete()

# Удалить по фильтру (без загрузки)
await User.find(User.is_active == False).delete()

# Удалить все
await User.delete_all()
```

---

## 9. Фильтры и операторы запросов

### 9.1 Сравнение

```python
User.age == 28          # равно
User.age != 28          # не равно
User.age > 18           # больше
User.age >= 18          # больше или равно
User.age < 65           # меньше
User.age <= 65          # меньше или равно
```

### 9.2 Логика AND / OR / NOR

```python
from beanie.odm.operators.find.logical import And, Or, Nor

# AND (через запятую в find — то же самое)
await User.find(User.age >= 18, User.is_active == True).to_list()
await User.find(And(User.age >= 18, User.is_active == True)).to_list()

# OR
await User.find(Or(User.age < 18, User.age > 65)).to_list()

# NOR
await User.find(Nor(User.is_active == True, User.age > 100)).to_list()
```

### 9.3 Массивы

```python
from beanie.odm.operators.find.array import All, ElemMatch

# Элемент входит в массив
await User.find(In(User.tags, ["admin", "moderator"])).to_list()

# Все элементы присутствуют
await User.find(All(User.tags, ["admin", "editor"])).to_list()
```

### 9.4 Строковый поиск (regex)

```python
import re
from beanie.odm.operators.find.evaluation import RegEx

# Поиск без учёта регистра
await User.find(RegEx(User.name, "alice", "i")).to_list()

# Через Python re
await User.find({"name": {"$regex": "^Alice", "$options": "i"}}).to_list()
```

### 9.5 In / NotIn

```python
from beanie.odm.operators.find.comparison import In, NotIn

await User.find(In(User.country, ["RU", "US", "DE"])).to_list()
await User.find(NotIn(User.country, ["XX", "YY"])).to_list()
```

### 9.6 Exists — проверка наличия поля

```python
from beanie.odm.operators.find.element import Exists

# Только документы где поле bio существует
await User.find(Exists(User.bio, True)).to_list()

# Только документы где поле bio отсутствует
await User.find(Exists(User.bio, False)).to_list()
```

### 9.7 Сырые MongoDB-запросы (когда Beanie не хватает)

```python
# find() принимает и обычные dict-фильтры
await User.find({"age": {"$gte": 18, "$lte": 65}}).to_list()

# Смешивание
await User.find(
    User.is_active == True,
    {"age": {"$gte": 18}},
).to_list()
```

---

## 10. Update — обновление документов

### 10.1 Операторы Update

```python
from beanie.odm.operators.update.general import Set, Unset, Inc, Push, Pop, Pull

# $set — установить значение
await User.find(User.name == "Alice").update(Set({User.age: 30}))

# $unset — удалить поле
await User.find(User.name == "Alice").update(Unset({User.bio: 1}))

# $inc — инкрементировать
await User.find(User.name == "Alice").update(Inc({User.age: 1}))

# $push — добавить в массив
await User.find(User.name == "Alice").update(Push({User.tags: "vip"}))

# $pull — удалить из массива по значению
await User.find(User.name == "Alice").update(Pull({User.tags: "old_tag"}))

# $pop — удалить первый (-1) или последний (1) элемент массива
await User.find(User.name == "Alice").update(Pop({User.tags: 1}))
```

### 10.2 Несколько операторов за раз

```python
# Обновить несколько полей одновременно
await User.find(User.name == "Alice").update(
    Set({User.age: 30, User.bio: "New bio"}),
    Push({User.tags: "vip"}),
)
```

### 10.3 find_one_and_update (атомарно найти и обновить)

```python
# Вернёт обновлённый документ
updated = await User.find_one_and_update(
    User.name == "Alice",
    Set({User.age: 30}),
    response_type=FindType.after,  # вернуть новый документ
)
print(updated.age)  # 30
```

---

## 11. Aggregation Pipeline

Aggregation — мощный инструмент для сложных запросов: группировка, join-ы, вычисления.

### 11.1 Через Beanie .aggregate()

```python
# Подсчёт пользователей по стране
pipeline = [
    {"$group": {"_id": "$country", "count": {"$sum": 1}}},
    {"$sort": {"count": -1}},
]

result = await User.aggregate(pipeline).to_list()
# → [{"_id": "RU", "count": 150}, {"_id": "US", "count": 120}]
```

### 11.2 Пример: среднее значение

```python
pipeline = [
    {"$match": {"is_active": True}},
    {"$group": {"_id": None, "avg_age": {"$avg": "$age"}}},
]

result = await User.aggregate(pipeline).to_list()
avg_age = result[0]["avg_age"] if result else 0
print(f"Средний возраст: {avg_age:.1f}")
```

### 11.3 Пример: $lookup (аналог JOIN)

```python
# Допустим: коллекция posts, каждый пост имеет author_id
# Хотим получить посты с данными автора

pipeline = [
    {
        "$lookup": {
            "from": "users",           # коллекция для join
            "localField": "author_id", # поле в posts
            "foreignField": "_id",     # поле в users
            "as": "author",            # результат — массив
        }
    },
    {"$unwind": "$author"},            # массив → объект (если один автор)
    {"$project": {"title": 1, "author.name": 1, "author.email": 1}},
]

result = await Post.aggregate(pipeline).to_list()
```

### 11.4 Aggregation с типизированным результатом

```python
from pydantic import BaseModel

class CountryStats(BaseModel):
    id: str = Field(alias="_id")
    count: int
    avg_age: float

pipeline = [
    {"$group": {
        "_id": "$country",
        "count": {"$sum": 1},
        "avg_age": {"$avg": "$age"},
    }},
]

stats = await User.aggregate(
    pipeline,
    projection_model=CountryStats,
).to_list()

for s in stats:
    print(f"{s.id}: {s.count} users, avg age {s.avg_age:.1f}")
```

---

## 12. Связи между документами — Link и BackLink

### 12.1 Link — ссылка на другой документ

```python
from beanie import Document, Link
from typing import Optional

class Category(Document):
    name: str

    class Settings:
        name = "categories"

class Post(Document):
    title: str
    content: str
    category: Link[Category]    # ссылка на Category

    class Settings:
        name = "posts"
```

```python
# Создание
category = Category(name="Technology")
await category.insert()

post = Post(title="Intro to Beanie", content="...", category=category)
await post.insert()
# В MongoDB сохранится {"category": ObjectId("...")}

# Чтение — без fetch_links ссылка не разворачивается
post = await Post.find_one(Post.title == "Intro to Beanie")
print(post.category)     # Link object (не полный документ)

# Чтение с разворачиванием ссылок
post = await Post.find_one(
    Post.title == "Intro to Beanie",
    fetch_links=True,    # ← разворачивает все Link-поля
)
print(post.category.name)   # "Technology"
```

### 12.2 BackLink — обратная ссылка

```python
from beanie import Document, Link, BackLink
from typing import List

class Author(Document):
    name: str
    posts: BackLink["Post"] = Field(original_field="author")  # обратная ссылка

    class Settings:
        name = "authors"

class Post(Document):
    title: str
    author: Link[Author]

    class Settings:
        name = "posts"
```

### 12.3 Optional Link

```python
class Post(Document):
    title: str
    category: Optional[Link[Category]] = None  # необязательная ссылка
```

---

## 13. Инициализация в FastAPI lifespan

### 13.1 Полный шаблон

```python
# db.py
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from src.models.user import User
from src.models.post import Post

motor_client: AsyncIOMotorClient | None = None

async def connect_db(mongo_url: str, db_name: str):
    global motor_client
    motor_client = AsyncIOMotorClient(mongo_url)
    db = motor_client[db_name]
    await init_beanie(
        database=db,
        document_models=[User, Post],  # все модели
    )

async def close_db():
    if motor_client:
        motor_client.close()
```

```python
# app.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.db import connect_db, close_db
from src.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_db(settings.MONGO_URL, settings.MONGO_DB)
    print("MongoDB connected")
    yield
    # Shutdown
    await close_db()
    print("MongoDB disconnected")

app = FastAPI(lifespan=lifespan)
```

```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MONGO_URL: str = "mongodb://localhost:27017"
    MONGO_DB: str = "my_database"

    class Config:
        env_file = ".env"

settings = Settings()
```

```env
# .env
MONGO_URL=mongodb://root:secret@localhost:27017/?authSource=admin
MONGO_DB=my_database
```

### 13.2 Маршруты FastAPI с Beanie

```python
# routes/users.py
from fastapi import APIRouter, HTTPException
from beanie import PydanticObjectId
from src.models.user import User
from src.schemas.user import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=UserResponse, status_code=201)
async def create_user(body: UserCreate):
    # Проверить уникальность email
    existing = await User.find_one(User.email == body.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(**body.model_dump())
    await user.insert()
    return user

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: PydanticObjectId):
    user = await User.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/", response_model=list[UserResponse])
async def list_users(skip: int = 0, limit: int = 20):
    users = await User.find().skip(skip).limit(limit).to_list()
    return users

@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(user_id: PydanticObjectId, body: UserUpdate):
    user = await User.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    await user.save()
    return user

@router.delete("/{user_id}", status_code=204)
async def delete_user(user_id: PydanticObjectId):
    user = await User.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await user.delete()
```

---

## 14. Репозиторий — паттерн доступа к данным

Репозиторий — слой между сервисом и базой данных. Изолирует логику запросов.

```python
# repositories/user_repository.py
from typing import Optional
from beanie import PydanticObjectId
from src.models.user import User

class UserRepository:

    async def get_by_id(self, user_id: PydanticObjectId) -> Optional[User]:
        return await User.get(user_id)

    async def get_by_email(self, email: str) -> Optional[User]:
        return await User.find_one(User.email == email)

    async def get_all(self, skip: int = 0, limit: int = 20) -> list[User]:
        return await User.find().skip(skip).limit(limit).to_list()

    async def create(self, data: dict) -> User:
        user = User(**data)
        await user.insert()
        return user

    async def update(self, user: User, data: dict) -> User:
        for field, value in data.items():
            setattr(user, field, value)
        await user.save()
        return user

    async def delete(self, user: User) -> None:
        await user.delete()

    async def count(self) -> int:
        return await User.count()

    async def exists_by_email(self, email: str) -> bool:
        return await User.find_one(User.email == email) is not None
```

```python
# services/user_service.py
from src.repositories.user_repository import UserRepository
from src.schemas.user import UserCreate

class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    async def register(self, data: UserCreate) -> User:
        if await self.repo.exists_by_email(data.email):
            raise ValueError("Email already registered")
        return await self.repo.create(data.model_dump())

    async def get_user_or_404(self, user_id: str) -> User:
        from beanie import PydanticObjectId
        user = await self.repo.get_by_id(PydanticObjectId(user_id))
        if not user:
            raise ValueError("User not found")
        return user
```

---

## 15. Тестирование с mongomock / mongomock-motor

### 15.1 Установка

```bash
pip install mongomock-motor pytest pytest-asyncio
```

### 15.2 Фикстура для тестов

```python
# tests/conftest.py
import pytest_asyncio
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie
from src.models.user import User
from src.models.post import Post

@pytest_asyncio.fixture
async def beanie_client():
    """Инициализирует Beanie с in-memory MongoDB для тестов"""
    client = AsyncMongoMockClient()
    db = client["test_db"]
    await init_beanie(
        database=db,
        document_models=[User, Post],
    )
    yield
    # После теста — коллекции очищаются автоматически (in-memory)
```

### 15.3 Пример теста

```python
# tests/test_user_repository.py
import pytest
from src.models.user import User
from src.repositories.user_repository import UserRepository

@pytest.mark.asyncio
async def test_create_user(beanie_client):
    repo = UserRepository()
    user = await repo.create({
        "name": "Alice",
        "email": "alice@example.com",
        "age": 28,
    })
    assert user.id is not None
    assert user.name == "Alice"

@pytest.mark.asyncio
async def test_get_by_email(beanie_client):
    # Вставить напрямую
    user = User(name="Bob", email="bob@example.com", age=30)
    await user.insert()

    repo = UserRepository()
    found = await repo.get_by_email("bob@example.com")
    assert found is not None
    assert found.name == "Bob"

@pytest.mark.asyncio
async def test_email_uniqueness(beanie_client):
    user1 = User(name="Alice", email="alice@example.com", age=28)
    await user1.insert()

    from src.services.user_service import UserService
    from src.schemas.user import UserCreate

    service = UserService(UserRepository())
    with pytest.raises(ValueError, match="Email already registered"):
        await service.register(UserCreate(name="Alice2", email="alice@example.com", age=20))
```

---

## 16. Docker — MongoDB для разработки

### 16.1 docker-compose.yml

```yaml
services:
  mongo:
    image: mongo:7
    container_name: app-mongo
    restart: unless-stopped
    ports:
      - "27017:27017"
    environment:
      MONGO_INITDB_ROOT_USERNAME: root
      MONGO_INITDB_ROOT_PASSWORD: secret
    volumes:
      - mongo_data:/data/db
    healthcheck:
      test:
        [
          "CMD", "mongosh",
          "--quiet",
          "--username", "root",
          "--password", "secret",
          "--authenticationDatabase", "admin",
          "--eval", "quit(db.adminCommand({ ping: 1 }).ok ? 0 : 2)",
        ]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 20s

volumes:
  mongo_data:
```

### 16.2 .env для приложения

```env
MONGO_URL=mongodb://root:secret@localhost:27017/?authSource=admin
MONGO_DB=my_database
```

### 16.3 URI форматы

```
# Без аутентификации
mongodb://localhost:27017

# С аутентификацией
mongodb://user:password@host:27017/?authSource=admin

# Atlas (облако)
mongodb+srv://user:password@cluster0.xxxxx.mongodb.net/

# Несколько хостов (replica set)
mongodb://host1:27017,host2:27017,host3:27017/?replicaSet=rs0
```

### 16.4 Команды mongosh

```bash
# Войти в контейнер
docker exec -it app-mongo mongosh -u root -p secret --authenticationDatabase admin

# В mongosh:
show dbs                          # список баз
use my_database                   # переключиться на базу
show collections                  # список коллекций
db.users.find().pretty()          # все документы
db.users.countDocuments()         # количество
db.users.find({"age": {"$gte": 18}})  # с фильтром
db.users.createIndex({"email": 1}, {unique: true})  # создать индекс
db.users.getIndexes()             # посмотреть индексы
db.users.drop()                   # удалить коллекцию
```

---

## 17. Частые ошибки

| Ошибка | Причина | Решение |
|---|---|---|
| `CollectionWasNotInitialized` | Забыл вызвать `init_beanie()` | Вызови `init_beanie()` до первого запроса |
| `ServerSelectionTimeoutError` | MongoDB не запущена или неверный URI | Проверь `docker ps` и URI в .env |
| `DuplicateKeyError` | Нарушение уникального индекса | Поймай исключение и верни 409 Conflict |
| `ValidationError` | Данные не прошли Pydantic-валидацию | Проверь типы и ограничения в модели |
| `AttributeError: 'coroutine'` | Забыл `await` | Добавь `await` перед запросом |
| `find()` вернул курсор, а не список | `find()` сам по себе курсор | Добавь `.to_list()` |
| `user.category` — Link, а не объект | Не передан `fetch_links=True` | Добавь `fetch_links=True` в `find_one` |
| `init_beanie` вызван до Motor-клиента | Неверный порядок инициализации | Сначала `AsyncIOMotorClient`, потом `init_beanie` |
| Изменения не сохраняются в БД | Изменил поля но не вызвал `save()` | После изменений вызови `await user.save()` |
| `PydanticObjectId` vs `ObjectId` | Разные типы для Beanie и PyMongo | В Beanie используй `PydanticObjectId` |

---

## 18. Быстрая шпаргалка

### Подключение + инициализация

```python
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client["my_db"]
await init_beanie(database=db, document_models=[User, Post])
```

### Минимальная модель

```python
from beanie import Document, Indexed
from pydantic import EmailStr

class User(Document):
    name: str
    email: Indexed(EmailStr, unique=True)
    age: int = 0

    class Settings:
        name = "users"
```

### CRUD одной страницей

```python
# Create
user = User(name="Alice", email="alice@example.com", age=28)
await user.insert()

# Read one
user = await User.find_one(User.email == "alice@example.com")
user = await User.get("64f1a2b3...")  # по id

# Read many
users = await User.find(User.age >= 18).sort(-User.age).limit(10).to_list()

# Update
user.age = 29
await user.save()

# Update без загрузки
from beanie.odm.operators.update.general import Set
await User.find(User.name == "Alice").update(Set({User.age: 29}))

# Delete
await user.delete()
await User.find(User.is_active == False).delete()

# Count
count = await User.find(User.is_active == True).count()
```

### Все операторы фильтрации

```python
User.age == 28          # eq
User.age != 28          # ne
User.age > 18           # gt
User.age >= 18          # gte
User.age < 65           # lt
User.age <= 65          # lte

In(User.country, ["RU", "US"])      # $in
NotIn(User.country, ["XX"])         # $nin
Exists(User.bio, True)              # $exists
RegEx(User.name, "alice", "i")      # $regex

Or(cond1, cond2)        # $or
And(cond1, cond2)       # $and
```

### Aggregation

```python
pipeline = [
    {"$match": {"is_active": True}},
    {"$group": {"_id": "$country", "count": {"$sum": 1}}},
    {"$sort": {"count": -1}},
]
result = await User.aggregate(pipeline).to_list()
```

### Стек зависимостей

```
beanie      ← ODM (Document, Indexed, init_beanie)
motor       ← AsyncIOMotorClient (async driver)
pymongo     ← IndexModel, ASCENDING, DESCENDING (низкий уровень)
```

---

## Ссылки

- [Beanie документация](https://beanie-odm.dev/)
- [Motor документация](https://motor.readthedocs.io/)
- [PyMongo документация](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/)
- [MongoDB операторы запросов](https://www.mongodb.com/docs/manual/reference/operator/query/)
- [MongoDB aggregation](https://www.mongodb.com/docs/manual/aggregation/)
- [mongomock-motor](https://github.com/michaelkryukov/mongomock_motor)
