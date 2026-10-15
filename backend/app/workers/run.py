"""Starting the worker (02 §3.3): inline in the API process, or as its own process.

- `WORKER_MODE=inline` (default): `inline_worker` runs the ingest loop as an asyncio task for
  the lifetime of the API (see the `main.py` lifespan).
- `WORKER_MODE=separate`: `python -m app.workers.run` runs the loop until SIGINT or SIGTERM;
  the API then starts no worker.
"""

import asyncio
import contextlib
import signal
from collections.abc import AsyncIterator

import structlog

from app.core.clock import SystemClock
from app.core.config import settings
from app.core.logging import setup_logging
from app.db.session import async_session_factory, engine
from app.workers.queue import IngestWorker

log = structlog.get_logger(__name__)

SHUTDOWN_GRACE_SECONDS = 10.0


def build_worker() -> IngestWorker:
    return IngestWorker(async_session_factory, SystemClock(), listen_engine=engine)


async def stop_worker(task: "asyncio.Task[None]", stop: asyncio.Event) -> None:
    """Ask the loop to stop after its current event; cancel it if that takes too long."""
    stop.set()
    try:
        await asyncio.wait_for(task, SHUTDOWN_GRACE_SECONDS)
    except TimeoutError:
        log.warning("worker_stop_timeout")  # cancelled; its claims are re-queued after 5 min


@contextlib.asynccontextmanager
async def inline_worker(enabled: bool) -> AsyncIterator[None]:
    """Run the ingest loop in this process while the context is open (when `enabled`)."""
    if not enabled:
        yield
        return
    stop = asyncio.Event()
    task = asyncio.create_task(build_worker().run(stop), name="ingest-worker")
    log.info("worker_started", mode="inline")
    try:
        yield
    finally:
        await stop_worker(task, stop)
        log.info("worker_stopped", mode="inline")


async def run_separate(stop: asyncio.Event) -> None:
    """Run the ingest loop until `stop` is set (by SIGINT or SIGTERM from `main`)."""
    log.info("worker_started", mode="separate")
    task = asyncio.create_task(build_worker().run(stop), name="ingest-worker")
    await stop.wait()
    await stop_worker(task, stop)
    await engine.dispose()
    log.info("worker_stopped", mode="separate")


async def _main() -> None:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    await run_separate(stop)


def main() -> None:
    setup_logging(settings.LOG_LEVEL)
    asyncio.run(_main())


if __name__ == "__main__":
    main()
