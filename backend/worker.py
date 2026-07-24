"""Worker para arrancar el scheduler."""

import asyncio
import logging

from app.tasks.scheduler import build_scheduler

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    scheduler = build_scheduler()
    scheduler.start()
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
