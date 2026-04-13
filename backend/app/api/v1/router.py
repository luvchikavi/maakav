"""API v1 router - aggregates all route modules."""

from fastapi import APIRouter
from .auth import router as auth_router
from .projects import router as projects_router
from .setup.budget import router as budget_router
from .setup.apartments import router as apartments_router
from .setup.financing import router as financing_router
from .monthly.reports import router as reports_router
from .monthly.bank_statements import router as bank_router
from .monthly.construction import router as construction_router
from .monthly.sales import router as sales_router
from .monthly.calculations import router as calculations_router
from .monthly.generation import router as generation_router

api_router = APIRouter(prefix="/api/v1")

# Auth
api_router.include_router(auth_router)

# Projects
api_router.include_router(projects_router)

# Setup
api_router.include_router(budget_router)
api_router.include_router(apartments_router)
api_router.include_router(financing_router)

# Monthly
api_router.include_router(reports_router)
api_router.include_router(bank_router)
api_router.include_router(construction_router)
api_router.include_router(sales_router)
api_router.include_router(calculations_router)
api_router.include_router(generation_router)
