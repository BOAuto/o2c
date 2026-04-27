from fastapi import APIRouter

from app.api.routes import (
    branches,
    companies,
    documents,
    login,
    mail_access,
    private,
    rate_contracts,
    temporal,
    users,
    utils,
    validations,
)
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(documents.router)
api_router.include_router(temporal.router)
api_router.include_router(mail_access.router)
api_router.include_router(companies.router)
api_router.include_router(rate_contracts.router)
api_router.include_router(validations.router)
api_router.include_router(branches.router)


if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
