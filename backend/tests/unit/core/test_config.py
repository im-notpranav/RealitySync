import pytest


def test_worker_mode_validation() -> None:
    # Must import fresh to avoid cached instance, but since we test validation,
    # we can just instantiate the class.
    from app.core.config import Settings

    # Default should work
    settings = Settings(JWT_SECRET="test", WORKER_MODE="inline", EVENT_BUS="memory")  # type: ignore
    assert settings.WORKER_MODE == "inline"

    # separate + pg_notify should work
    settings = Settings(JWT_SECRET="test", WORKER_MODE="separate", EVENT_BUS="pg_notify")  # type: ignore
    assert settings.WORKER_MODE == "separate"

    # separate + memory should fail
    with pytest.raises(ValueError, match="WORKER_MODE=separate requires EVENT_BUS=pg_notify"):
        Settings(JWT_SECRET="test", WORKER_MODE="separate", EVENT_BUS="memory")  # type: ignore
