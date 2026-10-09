import logging

from app.core.logging import pii_scrubber


def test_pii_scrubber() -> None:
    logger = logging.getLogger("test")

    event = {
        "message": "User created",
        "email": "john.doe@example.com",
        "phone": "+12345678901",
        "other": "Hello john.doe@example.com! Call me at 9876543210",
        "count": 5,
    }

    scrubbed = pii_scrubber(logger, "test_event", event)

    assert scrubbed["email"] == "j***@example.com"
    assert scrubbed["phone"] == "***01"
    assert scrubbed["other"] == "Hello j***@example.com! Call me at ***10"
    assert scrubbed["count"] == 5
    assert scrubbed["message"] == "User created"
