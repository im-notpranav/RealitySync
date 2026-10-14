"""The ingest loop: drains `ingest_events` (02 §3.3, 03 §M1, FR-ING-006/009, NFR-REL-001/002).

- **Claim:** a batch of `pending` events moves to `processing` in one short transaction
  (`FOR UPDATE SKIP LOCKED`, oldest first); each claim sets `locked_at` and increments
  `attempts`. The `(id, attempts)` pair is the claim's lease: whoever holds an older value has
  lost the event to a re-queue and must not touch it.
- **Process:** one transaction per event: lock the row, run `pipeline.process_event`, mark it
  `processed`. On an exception the transaction is rolled back and the failure is recorded in a
  new one: back to `pending` while `attempts < 5`, else `failed` (an admin can retry it).
- **Re-queue:** `processing` rows locked more than 5 minutes ago (a crashed worker) go back to
  `pending`, or to `failed` once they used 5 attempts. Rows a live worker is processing are row
  locked and skipped.
- **Wake-up:** `LISTEN ingest_pending` (sent by the ingest API on commit), with a 1 s polling
  fallback, so a lost notification or listener connection only adds latency.

Several workers may run at once (inline and `separate`); `SKIP LOCKED` keeps them apart.
"""

import asyncio
import contextlib
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import case, select, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.clock import Clock
from app.models import IngestEvent
from app.services.ingest_service import INGEST_CHANNEL
from app.workers import pipeline

log = structlog.get_logger(__name__)

MAX_ATTEMPTS = 5
STUCK_AFTER = timedelta(minutes=5)
POLL_INTERVAL_SECONDS = 1.0
BATCH_SIZE = 100
TIMED_OUT = "processing timed out"
_MAX_ERROR_CHARS = 500

ProcessEvent = Callable[[AsyncSession, IngestEvent], Awaitable[None]]


@dataclass(frozen=True)
class Claim:
    """One claimed event and the `attempts` value its claim set (the lease)."""

    id: uuid.UUID
    attempt: int


def describe_error(exc: BaseException) -> str:
    """The text stored in `ingest_events.error`: never record data (05 §2.5).

    Only `PipelineError` messages are trusted to be PII-free; anything else is reduced to its
    class name, because driver and library messages can quote the values involved.
    """
    if isinstance(exc, pipeline.PipelineError) and str(exc):
        return str(exc)[:_MAX_ERROR_CHARS]
    return type(exc).__name__


def _after_failure() -> Any:
    """`failed` once the event used all its attempts, else back to `pending`."""
    return case((IngestEvent.attempts >= MAX_ATTEMPTS, "failed"), else_="pending")


async def claim_batch(session: AsyncSession, *, now: datetime, limit: int) -> list[Claim]:
    """Move up to `limit` pending events (oldest first) to `processing` and commit."""
    due = (
        select(IngestEvent.id)
        .where(IngestEvent.status == "pending")
        .order_by(IngestEvent.received_at, IngestEvent.id)
        .limit(limit)
        .with_for_update(skip_locked=True)
        .scalar_subquery()
    )
    rows = await session.execute(
        update(IngestEvent)
        .where(IngestEvent.id.in_(due))
        .values(status="processing", locked_at=now, attempts=IngestEvent.attempts + 1)
        .returning(IngestEvent.id, IngestEvent.attempts, IngestEvent.received_at)
        .execution_options(synchronize_session=False)
    )
    claimed = sorted(rows.all(), key=lambda row: (row.received_at, row.id))
    await session.commit()
    return [Claim(id=row.id, attempt=row.attempts) for row in claimed]


async def requeue_stuck(session: AsyncSession, *, now: datetime) -> int:
    """Release events a crashed worker left in `processing` for over 5 minutes; commit."""
    stuck = (
        select(IngestEvent.id)
        .where(IngestEvent.status == "processing", IngestEvent.locked_at < now - STUCK_AFTER)
        .with_for_update(skip_locked=True)
        .scalar_subquery()
    )
    rows = await session.execute(
        update(IngestEvent)
        .where(IngestEvent.id.in_(stuck))
        .values(status=_after_failure(), error=TIMED_OUT, locked_at=None)
        .returning(IngestEvent.status)
        .execution_options(synchronize_session=False)
    )
    statuses = list(rows.scalars())
    await session.commit()
    if statuses:
        log.warning(
            "ingest_events_requeued",
            requeued=statuses.count("pending"),
            failed=statuses.count("failed"),
        )
    return len(statuses)


async def process_claim(
    session_factory: async_sessionmaker[AsyncSession],
    claim: Claim,
    *,
    now: datetime,
    process: ProcessEvent,
) -> str:
    """Process one claimed event. Returns its new status, or `lost` when the claim expired."""
    async with session_factory() as session:
        event = await session.scalar(
            select(IngestEvent)
            .where(
                IngestEvent.id == claim.id,
                IngestEvent.status == "processing",
                IngestEvent.attempts == claim.attempt,
            )
            .with_for_update()
        )
        if event is None:
            return "lost"
        try:
            await process(session, event)
            event.status = "processed"
            event.processed_at = now
            event.locked_at = None
            event.error = None
            await session.commit()
            return "processed"
        except Exception as exc:  # noqa: BLE001 - every failure is recorded on the event
            await session.rollback()
            error = describe_error(exc)

    async with session_factory() as session:
        status = await session.scalar(
            update(IngestEvent)
            .where(
                IngestEvent.id == claim.id,
                IngestEvent.status == "processing",
                IngestEvent.attempts == claim.attempt,
            )
            .values(status=_after_failure(), error=error, locked_at=None)
            .returning(IngestEvent.status)
            .execution_options(synchronize_session=False)
        )
        await session.commit()
    log.warning(
        "ingest_event_failed",
        event_id=str(claim.id),
        attempt=claim.attempt,
        error=error,
        status=status or "lost",
    )
    return status or "lost"


class IngestWorker:
    """Claims and processes ingest events until stopped."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        clock: Clock,
        *,
        listen_engine: AsyncEngine | None = None,
        process: ProcessEvent = pipeline.process_event,
        batch_size: int = BATCH_SIZE,
        poll_interval: float = POLL_INTERVAL_SECONDS,
    ) -> None:
        self._session_factory = session_factory
        self._clock = clock
        self._listen_engine = listen_engine
        self._process = process
        self._batch_size = batch_size
        self._poll_interval = poll_interval
        self._wake = asyncio.Event()

    async def run_once(self) -> int:
        """Re-queue stuck events, then claim and process one batch. Returns the batch size."""
        async with self._session_factory() as session:
            await requeue_stuck(session, now=self._clock.now())
            claims = await claim_batch(session, now=self._clock.now(), limit=self._batch_size)
        for claim in claims:
            await process_claim(
                self._session_factory, claim, now=self._clock.now(), process=self._process
            )
        return len(claims)

    async def run(self, stop: asyncio.Event) -> None:
        """Loop until `stop` is set. Errors are logged and retried after the poll interval."""
        async with contextlib.AsyncExitStack() as stack:
            await self._listen(stack)
            while not stop.is_set():
                self._wake.clear()  # a NOTIFY during this batch makes the wait return at once
                try:
                    handled = await self.run_once()
                except Exception as exc:  # noqa: BLE001 - the loop must survive DB outages
                    log.warning("ingest_loop_error", error=type(exc).__name__)
                    handled = 0
                if handled == 0:
                    await self._wait(stop)

    def _on_notify(self, *_args: object) -> None:
        self._wake.set()

    async def _listen(self, stack: contextlib.AsyncExitStack) -> None:
        """`LISTEN ingest_pending` on a dedicated connection; polling covers any failure."""
        if self._listen_engine is None:
            return
        try:
            conn = await stack.enter_async_context(self._listen_engine.connect())
            raw = await conn.get_raw_connection()
            driver: Any = raw.driver_connection  # the asyncpg connection
            await driver.add_listener(INGEST_CHANNEL, self._on_notify)
        except Exception as exc:  # noqa: BLE001 - fall back to polling
            log.warning("ingest_listen_unavailable", error=type(exc).__name__)
            return

        async def unlisten() -> None:
            with contextlib.suppress(Exception):
                await driver.remove_listener(INGEST_CHANNEL, self._on_notify)

        stack.push_async_callback(unlisten)

    async def _wait(self, stop: asyncio.Event) -> None:
        """Until a NOTIFY arrives, `stop` is set, or the poll interval passes."""
        waits = [asyncio.create_task(self._wake.wait()), asyncio.create_task(stop.wait())]
        try:
            await asyncio.wait(
                waits, timeout=self._poll_interval, return_when=asyncio.FIRST_COMPLETED
            )
        finally:
            for task in waits:
                task.cancel()
