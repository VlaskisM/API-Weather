from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):

    MONGO_PORT: int
    MONGO_HOST: str
    MONGO_DB_NAME: str
    OWM_API_KEY: str
    OWM_URL: str

    @property
    def mongo_url(self) -> str:
        return f"mongodb://{self.MONGO_HOST}:{self.MONGO_PORT}"

    model_config = SettingsConfigDict(env_file=Path(__file__).parent.parent / ".env")

settings = Settings()