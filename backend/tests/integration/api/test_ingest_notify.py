"""Accepted batches wake the ingest worker with `NOTIFY ingest_pending` after commit (02 §3.3).

These tests commit for real (Postgres delivers NOTIFY only on commit), so they do not use the
rolled-back `db_session`: its uncommitted rows would hold locks these sessions wait for.
"""

import asyncio
from collections.abc import AsyncGenerator, Awaitable, Callable

import asyncpg
import pytest
import pytest_asyncio
from authkit import START
from ingestkit import ACCOUNT_EVENT, event
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.db.seed import default_source_systems
from app.models import IngestEvent, SourceSystem
from app.services import ingest_service
from app.services.ingest_service import IngestCaller

pytestmark = [pytest.mark.db, pytest.mark.asyncio]


Committed = tuple[async_sessionmaker[AsyncSession], asyncpg.Connection]


@pytest_asyncio.fixture
async def committed(db_engine: AsyncEngine, database_url: str) -> AsyncGenerator[Committed, None]:
    """Sessions whose commits are real (NOTIFY is delivered only on commit) and a listening
    connection. Everything created here is deleted afterwards."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        created = list(
            await session.scalars(
                insert(SourceSystem)
                .values(default_source_systems())
                .on_conflict_do_nothing(index_elements=["key"])
                .returning(SourceSystem.id)
            )
        )
        await session.commit()
    listener = await asyncpg.connect(database_url.replace("postgresql+asyncpg", "postgresql"))
    try:
        yield factory, listener
    finally:
        await listener.close()
        async with factory() as session:
            await session.execute(delete(IngestEvent))
            await session.execute(delete(SourceSystem).where(SourceSystem.id.in_(created)))
            await session.commit()


async def notifications(
    listener: asyncpg.Connection, action: Callable[[], Awaitable[None]], timeout: float
) -> list[str]:
    received: list[str] = []
    arrived = asyncio.Event()

    def on_notify(_conn: object, _pid: int, _channel: str, payload: str) -> None:
        received.append(payload)
        arrived.set()

    await listener.add_listener("ingest_pending", on_notify)
    try:
        await action()
        try:
            await asyncio.wait_for(arrived.wait(), timeout)
        except TimeoutError:
            pass
    finally:
        await listener.remove_listener("ingest_pending", on_notify)
    return received


async def test_accepted_batches_wake_the_worker_after_commit(committed: Committed) -> None:
    factory, listener = committed
    batch_ids: list[str] = []

    async def ingest() -> None:
        async with factory() as session:
            accepted = await ingest_service.ingest_batch(
                session, caller=IngestCaller(), events=[ACCOUNT_EVENT], now=START
            )
            batch_ids.append(str(accepted.batch_id))

    assert await notifications(listener, ingest, timeout=2.0) == batch_ids


async def test_a_batch_with_nothing_new_does_not_wake_the_worker(committed: Committed) -> None:
    factory, listener = committed

    async def ingest_nothing() -> None:
        async with factory() as session:
            await ingest_service.ingest_batch(
                session, caller=IngestCaller(), events=[event(source="erp")], now=START
            )

    assert await notifications(listener, ingest_nothing, timeout=0.5) == []
