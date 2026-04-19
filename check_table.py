import asyncio
from sqlalchemy import text
from app.db.session import engine


async def check():
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables WHERE table_name = 'audit_logs'"
            )
        )
        print("audit_logs exists:", result.rowcount > 0)


asyncio.run(check())
