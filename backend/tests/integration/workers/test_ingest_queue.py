"""The ingest loop (T-044): claiming, processing, failures, crash recovery and wake-up.

The worker commits for real (and other workers must see those commits), so these tests use
committed sessions instead of the rolled-back `db_session`, and delete what they created.
"""

import asyncio
import uuid
from collections.abc import AsyncGenerator, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.db.seed import default_source_systems
from app.models import IngestEvent, SourceRecord, SourceSystem
from app.services import ingest_service
from app.services.ingest_service import IngestCaller
from app.workers import run
from app.workers.pipeline import PipelineError
from app.workers.queue import (
    MAX_ATTEMPTS,
    TIMED_OUT,
    Claim,
    IngestWorker,
    claim_batch,
    process_claim,
    requeue_stuck,
)

pytestmark = [pytest.mark.db, pytest.mark.asyncio]

START = datetime(2026, 10, 14, 9, 0, tzinfo=UTC)
Factory = async_sessionmaker[AsyncSession]


class MutableClock:
    def __init__(self, now: datetime) -> None:
        self.current = now

    def now(self) -> datetime:
        return self.current

    def advance(self, **delta: float) -> None:
        self.current += timedelta(**delta)


class Recorder:
    """A pipeline stand-in that records which events it saw."""

    def __init__(self, fail_with: Exception | None = None) -> None:
        self.seen: list[uuid.UUID] = []
        self.fail_with = fail_with

    async def __call__(self, session: AsyncSession, event: IngestEvent) -> None:
        self.seen.append(event.id)
        await asyncio.sleep(0)  # let concurrent workers interleave
        if self.fail_with is not None:
            raise self.fail_with


@pytest_asyncio.fixture
async def factory(db_engine: AsyncEngine) -> AsyncGenerator[Factory, None]:
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
    try:
        yield factory
    finally:
        async with factory() as session:
            await session.execute(delete(IngestEvent))
            await session.execute(delete(SourceRecord))  # versions cascade
            await session.execute(delete(SourceSystem).where(SourceSystem.id.in_(created)))
            await session.commit()


@pytest.fixture
def clock() -> MutableClock:
    return MutableClock(START)


async def add_events(factory: Factory, count: int, **values: Any) -> list[uuid.UUID]:
    """Insert `count` pending events received one second apart (oldest first)."""
    async with factory() as session:
        crm = await session.scalar(select(SourceSystem.id).where(SourceSystem.key == "crm"))
        rows = [
            {
                "batch_id": uuid.uuid4(),
                "source_system_id": crm,
                "record_type": "account",
                "external_id": f"C-{i}",
                "event_type": "upsert",
                "payload": {"name": "Jon Smith", "created_at": "2025-11-02T10:00:00Z"},
                "source_updated_at": START,
                "idempotency_key": uuid.uuid4().hex,
                "received_at": START + timedelta(seconds=i),
                **values,
            }
            for i in range(count)
        ]
        ids = list(
            await session.scalars(insert(IngestEvent).values(rows).returning(IngestEvent.id))
        )
        await session.commit()
    return ids


async def load(factory: Factory, event_id: uuid.UUID) -> IngestEvent:
    async with factory() as session:
        event = await session.get(IngestEvent, event_id)
        assert event is not None
        return event


async def statuses(factory: Factory) -> dict[str, int]:
    async with factory() as session:
        counts: dict[str, int] = {}
        for status in await session.scalars(select(IngestEvent.status)):
            counts[status] = counts.get(status, 0) + 1
        return counts


async def eventually(check: Callable[[], Any], timeout: float = 5.0) -> None:
    async def poll() -> None:
        while not await check():
            await asyncio.sleep(0.02)

    await asyncio.wait_for(poll(), timeout)


def worker(factory: Factory, clock: MutableClock, **options: Any) -> IngestWorker:
    return IngestWorker(factory, clock, **options)


# ------------------------------------------------------------------------- claim and process


async def test_pending_events_are_processed_oldest_first(
    factory: Factory, clock: MutableClock
) -> None:
    ids = await add_events(factory, 3)
    recorder = Recorder()

    handled = await worker(factory, clock, process=recorder).run_once()

    assert handled == 3
    assert recorder.seen == ids
    for event_id in ids:
        event = await load(factory, event_id)
        assert (event.status, event.attempts, event.error) == ("processed", 1, None)
        assert (event.processed_at, event.locked_at) == (START, None)


async def test_a_claim_takes_at_most_one_batch(factory: Factory, clock: MutableClock) -> None:
    await add_events(factory, 3)

    assert await worker(factory, clock, process=Recorder(), batch_size=2).run_once() == 2
    assert await statuses(factory) == {"processed": 2, "pending": 1}


async def test_claiming_marks_events_processing(factory: Factory, clock: MutableClock) -> None:
    ids = await add_events(factory, 2)

    async with factory() as session:
        claims = await claim_batch(session, now=START, limit=10)

    assert claims == [Claim(id=ids[0], attempt=1), Claim(id=ids[1], attempt=1)]
    event = await load(factory, ids[0])
    assert (event.status, event.locked_at, event.attempts) == ("processing", START, 1)


async def test_processed_and_failed_events_are_not_claimed(
    factory: Factory, clock: MutableClock
) -> None:
    await add_events(factory, 1, status="processed")
    await add_events(factory, 1, status="failed", attempts=MAX_ATTEMPTS)

    assert await worker(factory, clock, process=Recorder()).run_once() == 0


async def test_the_default_pipeline_marks_events_processed(
    factory: Factory, clock: MutableClock
) -> None:
    (event_id,) = await add_events(factory, 1)

    await worker(factory, clock).run_once()  # the real pipeline.process_event

    assert (await load(factory, event_id)).status == "processed"


async def test_concurrent_workers_never_double_process(
    factory: Factory, clock: MutableClock
) -> None:
    ids = await add_events(factory, 60)
    recorder = Recorder()

    async def drain(w: IngestWorker) -> None:
        while await w.run_once():
            pass

    await asyncio.gather(
        *(drain(worker(factory, clock, process=recorder, batch_size=7)) for _ in range(4))
    )

    assert sorted(recorder.seen) == sorted(ids)  # every event exactly once
    assert await statuses(factory) == {"processed": 60}


async def test_claims_skip_events_another_worker_holds(
    factory: Factory, clock: MutableClock
) -> None:
    ids = await add_events(factory, 4)
    async with factory() as other_worker:
        # Another worker is in the middle of claiming the two oldest events.
        await other_worker.execute(
            select(IngestEvent.id).where(IngestEvent.id.in_(ids[:2])).with_for_update()
        )
        async with factory() as session:
            claims = await asyncio.wait_for(claim_batch(session, now=START, limit=10), 2)
        await other_worker.rollback()

    assert [c.id for c in claims] == ids[2:]  # no waiting, no double claim


# ---------------------------------------------------------------------------------- failures


async def test_failures_are_retried_then_left_failed(factory: Factory, clock: MutableClock) -> None:
    (event_id,) = await add_events(factory, 1)
    failing = worker(factory, clock, process=Recorder(RuntimeError("bad jon@example.com")))

    await failing.run_once()

    event = await load(factory, event_id)
    assert (event.status, event.attempts, event.error) == ("pending", 1, "RuntimeError")
    assert event.locked_at is None

    for _ in range(MAX_ATTEMPTS - 1):
        await failing.run_once()

    event = await load(factory, event_id)
    assert (event.status, event.attempts, event.error) == ("failed", MAX_ATTEMPTS, "RuntimeError")
    assert await failing.run_once() == 0  # stays failed until an admin retries it


async def test_errors_never_store_record_data(factory: Factory, clock: MutableClock) -> None:
    (event_id,) = await add_events(factory, 1)
    leak = ValueError("invalid input for query argument $1: 'jon@example.com' +919876543210")

    await worker(factory, clock, process=Recorder(leak)).run_once()

    assert (await load(factory, event_id)).error == "ValueError"


async def test_pipeline_errors_keep_their_message(factory: Factory, clock: MutableClock) -> None:
    (event_id,) = await add_events(factory, 1)

    await worker(
        factory, clock, process=Recorder(PipelineError("parent record missing"))
    ).run_once()

    assert (await load(factory, event_id)).error == "parent record missing"


async def test_a_failure_rolls_back_the_pipeline_work(
    factory: Factory, clock: MutableClock
) -> None:
    await add_events(factory, 1)

    async def half_done(session: AsyncSession, event: IngestEvent) -> None:
        await session.execute(
            update(SourceSystem).where(SourceSystem.key == "crm").values(name="changed")
        )
        raise RuntimeError("boom")

    await worker(factory, clock, process=half_done).run_once()

    async with factory() as session:
        name = await session.scalar(select(SourceSystem.name).where(SourceSystem.key == "crm"))
    assert name != "changed"


async def test_an_admin_retry_gives_one_more_attempt(factory: Factory, clock: MutableClock) -> None:
    # What `POST /ingest/events/{id}/retry` leaves behind: pending, attempts kept (D-064).
    (event_id,) = await add_events(factory, 1, attempts=MAX_ATTEMPTS, error="RuntimeError")

    await worker(factory, clock, process=Recorder(RuntimeError())).run_once()

    event = await load(factory, event_id)
    assert (event.status, event.attempts) == ("failed", MAX_ATTEMPTS + 1)

    async with factory() as session:
        await session.execute(
            update(IngestEvent).where(IngestEvent.id == event_id).values(status="pending")
        )
        await session.commit()
    await worker(factory, clock, process=Recorder()).run_once()

    event = await load(factory, event_id)
    assert (event.status, event.error) == ("processed", None)


# ----------------------------------------------------------------------------- crash recovery


async def crash_mid_batch(factory: Factory) -> list[Claim]:
    """A worker claims a batch and dies before processing it."""
    async with factory() as session:
        return await claim_batch(session, now=START, limit=10)


async def test_a_crashed_workers_events_are_requeued_after_5_minutes(
    factory: Factory, clock: MutableClock
) -> None:
    ids = await add_events(factory, 2)
    await crash_mid_batch(factory)
    survivor = worker(factory, clock, process=Recorder())

    clock.advance(minutes=4, seconds=59)
    assert await survivor.run_once() == 0
    assert await statuses(factory) == {"processing": 2}

    clock.advance(seconds=2)
    assert await survivor.run_once() == 2

    for event_id in ids:
        event = await load(factory, event_id)
        assert (event.status, event.attempts, event.error) == ("processed", 2, None)


async def test_a_requeued_event_records_the_timeout(factory: Factory, clock: MutableClock) -> None:
    (event_id,) = await add_events(factory, 1)
    await crash_mid_batch(factory)

    async with factory() as session:
        assert await requeue_stuck(session, now=START + timedelta(minutes=6)) == 1

    event = await load(factory, event_id)
    assert (event.status, event.attempts, event.error) == ("pending", 1, TIMED_OUT)
    assert event.locked_at is None


async def test_an_event_that_keeps_crashing_workers_ends_failed(
    factory: Factory, clock: MutableClock
) -> None:
    (event_id,) = await add_events(factory, 1, attempts=MAX_ATTEMPTS - 1)
    await crash_mid_batch(factory)

    async with factory() as session:
        await requeue_stuck(session, now=START + timedelta(minutes=6))

    event = await load(factory, event_id)
    assert (event.status, event.attempts, event.error) == ("failed", MAX_ATTEMPTS, TIMED_OUT)


async def test_a_worker_that_lost_its_claim_does_not_process(
    factory: Factory, clock: MutableClock
) -> None:
    (event_id,) = await add_events(factory, 1)
    (slow,) = await crash_mid_batch(factory)  # a worker stalls for over 5 minutes...
    later = START + timedelta(minutes=6)
    async with factory() as session:
        await requeue_stuck(session, now=later)
        (fresh,) = await claim_batch(session, now=later, limit=10)  # ...and another takes over
    recorder = Recorder()

    assert await process_claim(factory, slow, now=later, process=recorder) == "lost"
    assert await process_claim(factory, fresh, now=later, process=recorder) == "processed"
    assert recorder.seen == [event_id]


async def test_events_being_processed_are_not_requeued(
    factory: Factory, clock: MutableClock
) -> None:
    (event_id,) = await add_events(factory, 1)
    (claim,) = await crash_mid_batch(factory)
    in_pipeline = asyncio.Event()
    release = asyncio.Event()

    async def slow(session: AsyncSession, event: IngestEvent) -> None:
        in_pipeline.set()
        await release.wait()

    processing = asyncio.create_task(process_claim(factory, claim, now=START, process=slow))
    await in_pipeline.wait()
    async with factory() as session:
        requeue = requeue_stuck(session, now=START + timedelta(minutes=6))
        requeued = await asyncio.wait_for(requeue, 2)  # must not wait for the live worker
    release.set()

    assert requeued == 0  # the row is locked by the live worker
    assert await processing == "processed"
    assert (await load(factory, event_id)).status == "processed"


# ------------------------------------------------------------------------------- the loop


async def run_in_background(w: IngestWorker) -> tuple["asyncio.Task[None]", asyncio.Event]:
    stop = asyncio.Event()
    return asyncio.create_task(w.run(stop)), stop


async def processed(factory: Factory, count: int) -> bool:
    return (await statuses(factory)).get("processed", 0) == count


async def test_notify_wakes_the_worker(
    factory: Factory, clock: MutableClock, db_engine: AsyncEngine
) -> None:
    w = worker(factory, clock, listen_engine=db_engine, poll_interval=60)
    task, stop = await run_in_background(w)
    try:
        await asyncio.sleep(0.3)  # the first (empty) pass is over; the loop now waits
        async with factory() as session:
            await ingest_service.ingest_batch(
                session,
                caller=IngestCaller(),
                events=[
                    {
                        "source": "crm",
                        "record_type": "account",
                        "external_id": "C-1042",
                        "event_type": "upsert",
                        "source_updated_at": "2026-10-08T09:58:00Z",
                        "payload": {"name": "Jon Smith", "created_at": "2025-11-02T10:00:00Z"},
                    }
                ],
                now=START,
            )

        await eventually(lambda: processed(factory, 1), timeout=5)  # far below the 60 s poll
    finally:
        stop.set()
        await asyncio.wait_for(task, 5)


async def test_polling_finds_events_without_a_notification(
    factory: Factory, clock: MutableClock
) -> None:
    task, stop = await run_in_background(worker(factory, clock, poll_interval=0.05))
    try:
        await asyncio.sleep(0.1)
        await add_events(factory, 2)  # inserted directly: no NOTIFY

        await eventually(lambda: processed(factory, 2))
    finally:
        stop.set()
        await asyncio.wait_for(task, 5)


async def test_the_loop_survives_database_errors(clock: MutableClock) -> None:
    def broken() -> AsyncSession:
        raise ConnectionRefusedError

    w = IngestWorker(broken, clock, poll_interval=0.01)  # type: ignore[arg-type]
    task, stop = await run_in_background(w)
    await asyncio.sleep(0.1)

    assert not task.done()
    stop.set()
    await asyncio.wait_for(task, 5)


async def test_a_lost_listener_falls_back_to_polling(factory: Factory, clock: MutableClock) -> None:
    class BrokenEngine:
        def connect(self) -> Any:
            raise ConnectionRefusedError

    w = worker(factory, clock, listen_engine=BrokenEngine(), poll_interval=0.05)
    task, stop = await run_in_background(w)
    try:
        await add_events(factory, 1)
        await eventually(lambda: processed(factory, 1))
    finally:
        stop.set()
        await asyncio.wait_for(task, 5)


# ------------------------------------------------------------------------------ worker modes


@pytest.fixture
def test_worker(
    monkeypatch: pytest.MonkeyPatch, factory: Factory, clock: MutableClock, db_engine: AsyncEngine
) -> None:
    monkeypatch.setattr(
        run,
        "build_worker",
        lambda: IngestWorker(factory, clock, listen_engine=db_engine, poll_interval=0.05),
    )


def worker_tasks() -> list["asyncio.Task[Any]"]:
    return [t for t in asyncio.all_tasks() if t.get_name() == "ingest-worker" and not t.done()]


@pytest.mark.usefixtures("test_worker")
async def test_inline_mode_runs_the_loop_with_the_app(factory: Factory) -> None:
    async with run.inline_worker(enabled=True):
        assert len(worker_tasks()) == 1
        await add_events(factory, 1)
        await eventually(lambda: processed(factory, 1))

    assert worker_tasks() == []


@pytest.mark.usefixtures("test_worker")
async def test_separate_mode_starts_no_inline_worker() -> None:
    async with run.inline_worker(enabled=False):
        assert worker_tasks() == []


@pytest.mark.usefixtures("test_worker")
async def test_the_separate_process_runs_until_stopped(
    factory: Factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    class AppEngine:  # the shared app engine stays usable for the rest of the test session
        async def dispose(self) -> None:
            pass

    monkeypatch.setattr(run, "engine", AppEngine())
    stop = asyncio.Event()
    process = asyncio.create_task(run.run_separate(stop))
    await add_events(factory, 1)
    await eventually(lambda: processed(factory, 1))

    stop.set()
    await asyncio.wait_for(process, 5)
    assert worker_tasks() == []


async def test_stopping_cancels_a_loop_that_does_not_finish(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(run, "SHUTDOWN_GRACE_SECONDS", 0.05)
    task = asyncio.create_task(asyncio.sleep(60))

    await run.stop_worker(task, asyncio.Event())

    assert task.cancelled()


async def test_the_pipeline_turns_events_into_records(
    factory: Factory, clock: MutableClock
) -> None:
    await add_events(factory, 1)

    await worker(factory, clock).run_once()

    async with factory() as session:
        record = await session.scalar(select(SourceRecord))
    assert record is not None
    assert (record.external_id, record.normalized["name"]) == ("C-0", "jon smith")


async def test_unreadable_payloads_fail_with_the_field_name(
    factory: Factory, clock: MutableClock
) -> None:
    (event_id,) = await add_events(
        factory, 1, payload={"name": "Jon Smith", "created_at": "yesterday"}
    )

    await worker(factory, clock).run_once()

    event = await load(factory, event_id)
    assert (event.status, event.error) == ("pending", "payload.created_at is invalid")
