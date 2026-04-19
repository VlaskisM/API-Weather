from fastapi import FastAPI
from src.routes.cities import router as cities_router
from src.routes.weather import router as weather_router
from contextlib import asynccontextmanager
from src.db.db_mongo import conn


@asynccontextmanager
async def lifespan(app : FastAPI):
    try:
        await conn.init()
        yield
    finally:
        await conn.close()


app = FastAPI(lifespan=lifespan)

app.include_router(cities_router)
app.include_router(weather_router)

