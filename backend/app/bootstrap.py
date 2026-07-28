import asyncio
import logging

import app.models  # noqa: F401
from app.core.database import Base, engine

logger = logging.getLogger(__name__)


async def create_schema(max_attempts: int = 10, retry_delay_seconds: float = 2.0) -> None:
    for attempt in range(1, max_attempts + 1):
        try:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            return
        except Exception:
            if attempt == max_attempts:
                raise
            logger.warning(
                "Database is not ready; retrying schema creation in %.1f seconds (%d/%d)",
                retry_delay_seconds,
                attempt,
                max_attempts,
                exc_info=True,
            )
            await asyncio.sleep(retry_delay_seconds)


if __name__ == "__main__":
    asyncio.run(create_schema())
