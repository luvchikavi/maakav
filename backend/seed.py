"""Seed script - creates initial firm and admin user for local development."""

import asyncio
from app.database import engine, AsyncSessionLocal, Base
from app.models import *  # noqa - import all models so tables are registered
from app.models.user import UserRole
from app.core.security import hash_password


async def seed():
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created.")

    async with AsyncSessionLocal() as db:
        # Check if firm already exists
        from sqlalchemy import select
        result = await db.execute(select(Firm).where(Firm.name == "בלייר כץ-אהרונוב"))
        if result.scalar_one_or_none():
            print("Seed data already exists. Skipping.")
            return

        # Create firm
        firm = Firm(name="בלייר כץ-אהרונוב", contact_email="office@shamaot.co.il")
        db.add(firm)
        await db.flush()

        # Create admin user
        admin = User(
            firm_id=firm.id,
            email="admin@maakav.co.il",
            password_hash=hash_password("admin123"),
            first_name="אבי",
            last_name="לובצ'יק",
            role=UserRole.ADMIN,
        )
        db.add(admin)
        await db.commit()
        print(f"Created firm: {firm.name} (id={firm.id})")
        print(f"Created admin: {admin.email} / admin123")


if __name__ == "__main__":
    asyncio.run(seed())
