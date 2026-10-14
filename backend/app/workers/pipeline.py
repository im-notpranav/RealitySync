"""What the ingest loop does with one claimed event (02 §3.3, 03 §M1).

`process_event` runs inside the loop's per-event transaction; the loop marks the event
`processed` in that same transaction once it returns, or records the failure if it raises.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import IngestEvent


class PipelineError(Exception):
    """A failure whose message is safe to store as the event's `error`.

    The message must name fields or reasons only, never record values (05 §2.5: no PII).
    Any other exception is stored as its class name only.
    """


async def process_event(session: AsyncSession, event: IngestEvent) -> None:
    """Normalize the event and upsert its record (T-012). Until then events are only marked
    processed by the loop."""
