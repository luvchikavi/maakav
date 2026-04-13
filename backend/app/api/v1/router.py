"""API v1 router - aggregates all route modules."""

from fastapi import APIRouter
from .auth import router as auth_router
from .projects import router as projects_router
from .setup.budget import router as budget_router
from .setup.apartments import router as apartments_router
from .setup.financing import router as financing_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(projects_router)
api_router.include_router(budget_router)
api_router.include_router(apartments_router)
api_router.include_router(financing_router)
