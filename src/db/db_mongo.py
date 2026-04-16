from pymongo import AsyncMongoClient
from beanie import init_beanie

from src.config import settings
from src.models.model_city import City


class ConnectionMongo:
    client: AsyncMongoClient | None = None

    async def init(self):
        self.client = AsyncMongoClient(settings.mongo_url)
        db = self.client[settings.MONGO_DB_NAME]
        await init_beanie(database=db, document_models=[City])

    async def close(self):
        if self.client is not None:
            await self.client.close()
            self.client = None

    async def get_client(self):
        return self.client


conn = ConnectionMongo()
