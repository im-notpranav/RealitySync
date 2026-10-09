import logging
import re
import sys
from typing import Any

import structlog
import ulid
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_REGEX = re.compile(r"\+?\d{10,15}")

from collections.abc import Mapping, MutableMapping


def pii_scrubber(logger: Any, name: str, event_dict: MutableMapping[str, Any]) -> Mapping[str, Any]:
    """Masks emails and phones in log event dict"""
    for k, v in event_dict.items():
        if isinstance(v, str):
            # Mask emails to j***@domain.com
            def mask_email(match: re.Match[str]) -> str:
                email = match.group(0)
                parts = email.split("@")
                if len(parts) == 2:
                    return f"{parts[0][0]}***@{parts[1]}"
                return "***"

            # Mask phones to +***42
            def mask_phone(match: re.Match[str]) -> str:
                phone = match.group(0)
                return f"***{phone[-2:]}" if len(phone) > 2 else "***"

            v = EMAIL_REGEX.sub(mask_email, v)
            v = PHONE_REGEX.sub(mask_phone, v)
            event_dict[k] = v
    return event_dict


def setup_logging(log_level: str = "INFO") -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=log_level.upper())

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            pii_scrubber,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(ulid.ULID())
        request.state.request_id = request_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id, path=request.url.path, method=request.method
        )

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
