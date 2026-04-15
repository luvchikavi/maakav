"""Production startup: create tables + run server."""
import asyncio
import os
import subprocess
import sys

from dotenv import load_dotenv
load_dotenv()

# Import all models at module level so tables are registered
from app.database import engine, Base
from app.models import (  # noqa
    Firm, User, Project, ProjectFinancing, ContractorAgreement, Milestone,
    BudgetCategory, BudgetLineItem, Apartment, SalesContract, PaymentScheduleItem,
    MonthlyReport, BankStatement, BankTransaction, BudgetTrackingSnapshot,
    BudgetTrackingLine, ConstructionProgress, VatTracking, EquityTracking,
    GuaranteeSnapshot, ProfitabilitySnapshot, SourcesUses, PaymentApproval,
)


async def init_db():
    """Create all tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("Database tables verified.")


def main():
    # 1. Init DB tables
    asyncio.run(init_db())

    # 2. Start uvicorn
    port = os.environ.get("PORT", "8000")
    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", "0.0.0.0",
        "--port", port,
    ])


if __name__ == "__main__":
    main()
