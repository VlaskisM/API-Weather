from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):

    MONGO_PORT: int
    MONGO_HOST: str
    MONGO_DB_NAME: str
    OWM_API_KEY: str
    OWM_URL: str
    OWM_WEATHER_URL: str
    MONGO_INITDB_ROOT_USERNAME: str
    MONGO_INITDB_ROOT_PASSWORD: str
    REDIS_HOST: str
    REDIS_PORT: int

    @property
    def mongo_url(self) -> str:
        return f"mongodb://{self.MONGO_HOST}:{self.MONGO_PORT}/{self.MONGO_DB_NAME}"

    model_config = SettingsConfigDict(env_file=Path(__file__).parent.parent / ".env")

settings = Settings()