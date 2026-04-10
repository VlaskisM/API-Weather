from fastapi import FastAPI
from src.routes.cities import router as cities_router

app = FastAPI()

app.include_router(cities_router)

