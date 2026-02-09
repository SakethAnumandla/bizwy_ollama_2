from fastapi import APIRouter
from app.api.v1.endpoints import enrich

api_router = APIRouter()
api_router.include_router(enrich.router, prefix="/products", tags=["products"])
