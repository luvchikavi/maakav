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
    """Create all tables if they don't exist, and apply idempotent column additions."""
    from sqlalchemy import text
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Idempotent column additions — safe to run on every boot.
        column_additions = [
            "ALTER TABLE project_financing ADD COLUMN IF NOT EXISTS guarantee_frameworks JSON",
            "ALTER TABLE project_financing ADD COLUMN IF NOT EXISTS pre_project_investments JSON",
            "ALTER TABLE project_financing ADD COLUMN IF NOT EXISTS equity_required_after_presale NUMERIC(15, 2)",
            "ALTER TABLE sales_contracts ADD COLUMN IF NOT EXISTS vat_rate NUMERIC(5, 4)",
        ]
        for stmt in column_additions:
            try:
                await conn.execute(text(stmt))
            except Exception as e:
                print(f"Column-addition skipped ({stmt}): {e}")
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
