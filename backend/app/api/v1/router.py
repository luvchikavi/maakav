"""API v1 router - aggregates all route modules."""

from fastapi import APIRouter
from .auth import router as auth_router
from .projects import router as projects_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(projects_router)
