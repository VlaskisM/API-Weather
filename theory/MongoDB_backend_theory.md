# MongoDB: полная теория для бэкенда (с примерами)

## 1. Что это и как устроено

**MongoDB** — документо-ориентированная NoSQL СУБД. Данные хранятся как **документы** (JSON-подобные объекты) в **коллекциях** внутри **базы данных**.

| Реляционная СУБД | MongoDB        |
|------------------|----------------|
| Таблица          | Коллекция      |
| Строка           | Документ       |
| Колонка          | Поле           |
| JOIN             | `$lookup`, вложение, ручные запросы |

**BSON** — бинарное представление JSON с дополнительными типами: `ObjectId`, `Date`, `Binary`, `Decimal128` и т.д. Лимит размера одного документа — **16 МБ**.

**Основные компоненты:**

- **mongod** — сервер БД.
- **mongosh** — интерактивная оболочка (раньше `mongo`).
- **Replica Set** — несколько узлов с репликацией (высокая доступность).
- **Sharding** — горизонтальное разбиение данных по кластеру.

---

## 2. Установка и запуск (локально)

**Docker (типичный вариант для разработки):**

```yaml
# фрагмент docker-compose
services:
  mongo:
    image: mongo:7
    ports:
      - "27017:27017"
    environment:
      MONGO_INITDB_ROOT_USERNAME: root
      MONGO_INITDB_ROOT_PASSWORD: secret
```

Строка подключения:

```text
mongodb://root:secret@localhost:27017/?authSource=admin
```

**Без авторизации (только локально):**

```text
mongodb://localhost:27017
```

---

## 3. Подключение из Python (PyMongo, синхронно)

```bash
pip install pymongo
```

```python
from pymongo import MongoClient
from pymongo.server_api import ServerApi

# Локально без auth
client = MongoClient("mongodb://localhost:27017")

# С авторизацией и явной базой для учётных данных
uri = "mongodb://user:pass@localhost:27017/?authSource=admin"
client = MongoClient(uri)

db = client["myapp"]           # база данных
users = db["users"]          # коллекция

# Проверка соединения
client.admin.command("ping")
```

**Асинхронно (Motor — для FastAPI и т.п.):**

```bash
pip install motor
```

```python
from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client["myapp"]
users = db["users"]

# Пример: await users.find_one({"email": "a@b.com"})
```

---

## 4. Базовые сущности

- **`_id`** — первичный ключ. Если не указать при вставке, MongoDB создаст `ObjectId`.
- **База** — изолированный набор коллекций.
- **Коллекция** — не требует заранее описанной схемы (но схему можно задать валидацией).

Пример документа:

```json
{
  "_id": { "$oid": "6610..." },
  "email": "user@example.com",
  "profile": { "name": "Иван", "city": "Москва" },
  "tags": ["dev", "backend"],
  "createdAt": { "$date": "2026-04-09T12:00:00.000Z" }
}
```

---

## 5. CRUD в mongosh (оболочка)

Переключение базы и коллекции:

```javascript
use myapp
db.users.insertOne({ email: "a@b.com", name: "Ann" })
db.users.find()
db.users.findOne({ email: "a@b.com" })
```

### Create

```javascript
db.users.insertOne({ email: "b@c.com", name: "Bob", score: 0 })
db.users.insertMany([
  { email: "c@d.com", name: "Carl" },
  { email: "d@e.com", name: "Dan" }
])
```

### Read (find)

Фильтрация и операторы:

```javascript
// Равенство
db.users.find({ name: "Bob" })

// Сравнения: $gt, $gte, $lt, $lte, $ne
db.users.find({ score: { $gte: 10 } })

// Вхождение в список
db.users.find({ email: { $in: ["a@b.com", "b@c.com"] } })

// Логика: $and, $or, $not, $nor
db.users.find({ $or: [{ score: { $lt: 5 } }, { name: "Carl" }] })

// Существование поля
db.users.find({ city: { $exists: true } })

// Регулярное выражение (поиск по подстроке, осторожно с индексами)
db.users.find({ name: /^B/ })

// Проекция: только нужные поля (1 — включить, 0 — исключить _id)
db.users.find({}, { email: 1, name: 1, _id: 0 })

// Сортировка, пропуск, лимит
db.users.find().sort({ score: -1 }).skip(10).limit(5)
```

### Update

```javascript
// Обновить один документ
db.users.updateOne(
  { email: "a@b.com" },
  { $set: { city: "SPb" }, $inc: { score: 1 } }
)

// Массивы: $push, $pull, $addToSet
db.users.updateOne(
  { email: "a@b.com" },
  { $push: { tags: "mongodb" } }
)

// upsert: создать, если не нашли
db.users.updateOne(
  { email: "new@x.com" },
  { $set: { name: "New" } },
  { upsert: true }
)

// Много документов
db.users.updateMany({ score: { $lt: 0 } }, { $set: { score: 0 } })
```

### Delete

```javascript
db.users.deleteOne({ email: "a@b.com" })
db.users.deleteMany({ score: { $lt: -100 } })
```

---

## 6. CRUD в PyMongo (те же операции)

```python
from datetime import datetime, timezone
from bson import ObjectId

# Create
result = users.insert_one({
    "email": "x@y.com",
    "name": "X",
    "createdAt": datetime.now(timezone.utc),
})
print(result.inserted_id)

users.insert_many([{"email": "1@a.com"}, {"email": "2@a.com"}])

# Read
doc = users.find_one({"email": "x@y.com"})
for u in users.find({"score": {"$gte": 10}}).sort("score", -1).limit(5):
    print(u)

# По _id
oid = ObjectId("6610abcdef6610abcdef12")
users.find_one({"_id": oid})

# Update
users.update_one(
    {"email": "x@y.com"},
    {"$set": {"city": "MSK"}, "$inc": {"visits": 1}},
)
users.update_many({"inactive": True}, {"$set": {"archived": True}})

# Delete
users.delete_one({"email": "x@y.com"})
users.delete_many({"archived": True})
```

---

## 7. Индексы

Индексы ускоряют **чтение и сортировку** по заданным полям, но **замедляют вставку/обновление**.

```javascript
// Одно поле
db.users.createIndex({ email: 1 }, { unique: true })

// Составной (порядок важен: сначала равенство, потом диапазон)
db.orders.createIndex({ userId: 1, createdAt: -1 })

// TTL — автоудаление документов через N секунд (поле должно быть Date)
db.sessions.createIndex({ expiresAt: 1 }, { expireAfterSeconds: 0 })

// Текстовый поиск
db.articles.createIndex({ title: "text", body: "text" })

// Список индексов
db.users.getIndexes()
```

**PyMongo:**

```python
users.create_index([("email", 1)], unique=True)
users.create_index([("userId", 1), ("createdAt", -1)])
```

**Проверка плана запроса:**

```javascript
db.users.find({ email: "a@b.com" }).explain("executionStats")
```

Ищи `IXSCAN` (хорошо) vs `COLLSCAN` (полный перебор — плохо на больших коллекциях).

---

## 8. Aggregation Pipeline

Цепочка этапов: данные проходят через `$match` → `$group` → …

```javascript
db.orders.aggregate([
  { $match: { status: "paid", createdAt: { $gte: ISODate("2026-01-01") } } },
  {
    $group: {
      _id: "$userId",
      total: { $sum: "$amount" },
      count: { $sum: 1 },
    },
  },
  { $sort: { total: -1 } },
  { $limit: 10 },
])
```

**Связь коллекций (`$lookup` — аналог LEFT JOIN):**

```javascript
db.orders.aggregate([
  { $match: { _id: ObjectId("...") } },
  {
    $lookup: {
      from: "users",
      localField: "userId",
      foreignField: "_id",
      as: "user",
    },
  },
  { $unwind: "$user" },
])
```

**PyMongo:**

```python
pipeline = [
    {"$match": {"status": "paid"}},
    {"$group": {"_id": "$userId", "sum": {"$sum": "$amount"}}},
]
list(db["orders"].aggregate(pipeline))
```

---

## 9. Моделирование: embedding vs referencing

**Embedding** — вложить связанные данные в один документ (заказ и позиции внутри заказа).

- Плюсы: один запрос, быстрый типичный сценарий «прочитать заказ целиком».
- Минусы: дублирование, лимит 16 МБ, сложнее частично обновлять огромные вложения.

**Referencing** — хранить `userId` в заказе, пользователь в отдельной коллекции.

- Плюсы: нормализация, одно место правки профиля.
- Минусы: два запроса или aggregation с `$lookup`.

На практике часто **комбинируют**: часто читаемое — вложить, редкое и тяжёлое — по ссылке.

---

## 10. Транзакции (несколько операций атомарно)

Нужны **replica set** (или sharded cluster). В PyMongo:

```python
with client.start_session() as session:
    with session.start_transaction():
        db["accounts"].update_one(
            {"_id": acc_a},
            {"$inc": {"balance": -100}},
            session=session,
        )
        db["accounts"].update_one(
            {"_id": acc_b},
            {"$inc": {"balance": 100}},
            session=session,
        )
```

В mongosh аналогично через `session.startTransaction()` / `commitTransaction` / `abortTransaction`.

---

## 11. Валидация схемы (на уровне коллекции)

```javascript
db.createCollection("users", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["email", "createdAt"],
      properties: {
        email: { bsonType: "string", pattern: "^.+@.+$" },
        age: { bsonType: ["int", "long"], minimum: 0 },
        createdAt: { bsonType: "date" },
      },
    },
  },
  validationLevel: "strict",
  validationAction: "error",
})
```

---

## 12. Безопасность и эксплуатация

- Включить **аутентификацию**, не использовать пустой пароль в проде.
- Ограничить доступ по сети (firewall, только приложение и админы).
- **TLS** для соединений.
- Регулярные **бэкапы** (mongodump / облачные снапшоты) и тест восстановления.
- Не хранить секреты в коде — переменные окружения, секрет-хранилища.

---

## 13. Чек-лист для бэкенда

1. Строка подключения из конфига, один `MongoClient` на процесс (переиспользовать).
2. Индексы под реальные `find` + `sort` + уникальность там, где нужно.
3. Даты в **UTC**, в API отдавать ISO-8601.
4. Для тяжёлых отчётов — aggregation, не N+1 запросов в цикле.
5. Следить за `explain`, медленными запросами, размером документов.
6. При необходимости согласованности между коллекциями — транзакции.

---

## 14. Полезные ссылки

- Документация: [https://www.mongodb.com/docs/](https://www.mongodb.com/docs/)
- PyMongo: [https://www.mongodb.com/docs/languages/python/pymongo-driver/current/](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/)
- Motor: [https://motor.readthedocs.io/](https://motor.readthedocs.io/)

Файл можно дополнять своими заметками по конкретному проекту (схемы коллекций, индексы, примеры запросов из логов).
