"""What the ingest loop does with one claimed event (02 §3.3, 03 §M1).

`process_event` runs inside the loop's per-event transaction; the loop marks the event
`processed` in that same transaction once it returns, or records the failure if it raises.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import IngestEvent
from app.services import record_service, resolution_service
from app.services.record_service import InvalidRecord


class PipelineError(Exception):
    """A failure whose message is safe to store as the event's `error`.

    The message must name fields or reasons only, never record values (05 §2.5: no PII).
    Any other exception is stored as its class name only.
    """


async def process_event(session: AsyncSession, event: IngestEvent) -> None:
    """Normalize the event, upsert its record and history (T-012), then link it to an entity
    and request detection (T-017), all in the loop's transaction."""
    try:
        change = await record_service.apply_event(
            session, event, phone_region=settings.DEFAULT_PHONE_REGION
        )
    except InvalidRecord as exc:
        raise PipelineError(str(exc)) from exc
    if not change.state_changed:
        return
    await resolution_service.resolve(
        session, change, auto=settings.MATCH_AUTO, review=settings.MATCH_REVIEW
    )
    # `needs_review` links in the result raise `link_needs_review` alerts once T-045 exists.
