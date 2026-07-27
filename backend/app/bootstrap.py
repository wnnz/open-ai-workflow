import asyncio

import app.models  # noqa: F401
from app.core.database import Base, engine


async def create_schema() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(create_schema())
