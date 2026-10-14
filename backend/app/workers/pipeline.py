"""What the ingest loop does with one claimed event (02 §3.3, 03 §M1).

`process_event` runs inside the loop's per-event transaction; the loop marks the event
`processed` in that same transaction once it returns, or records the failure if it raises.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import IngestEvent
from app.services import record_service
from app.services.record_service import InvalidRecord


class PipelineError(Exception):
    """A failure whose message is safe to store as the event's `error`.

    The message must name fields or reasons only, never record values (05 §2.5: no PII).
    Any other exception is stored as its class name only.
    """


async def process_event(session: AsyncSession, event: IngestEvent) -> None:
    """Normalize the event and upsert its record and history (T-012)."""
    try:
        change = await record_service.apply_event(
            session, event, phone_region=settings.DEFAULT_PHONE_REGION
        )
    except InvalidRecord as exc:
        raise PipelineError(str(exc)) from exc
    if not change.state_changed:
        return
    # Entity resolution (T-017) hooks in here: resolve `change`, then request detection.
