from fastapi import APIRouter

from app.api.routes import documents, login, private, temporal, users, utils
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(documents.router)
api_router.include_router(temporal.router)


if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
