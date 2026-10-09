import pytest


def test_worker_mode_validation() -> None:
    # Must import fresh to avoid cached instance, but since we test validation,
    # we can just instantiate the class.
    from app.core.config import Settings

    # Default should work
    settings = Settings(JWT_SECRET="test", WORKER_MODE="inline", EVENT_BUS="memory")
    assert settings.WORKER_MODE == "inline"

    # separate + pg_notify should work
    settings = Settings(JWT_SECRET="test", WORKER_MODE="separate", EVENT_BUS="pg_notify")
    assert settings.WORKER_MODE == "separate"

    # separate + memory should fail
    with pytest.raises(ValueError, match="WORKER_MODE=separate requires EVENT_BUS=pg_notify"):
        Settings(JWT_SECRET="test", WORKER_MODE="separate", EVENT_BUS="memory")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("http://localhost:5173", ["http://localhost:5173"]),
        (
            "http://localhost:5173, http://127.0.0.1:5173",
            ["http://localhost:5173", "http://127.0.0.1:5173"],
        ),
        ('["http://localhost:5173"]', ["http://localhost:5173"]),
    ],
)
def test_cors_origins_parses_documented_env_formats(
    monkeypatch: pytest.MonkeyPatch, raw: str, expected: list[str]
) -> None:
    # Regression: the plain value from .env.example (02 §8) crashed startup with SettingsError.
    from app.core.config import Settings

    monkeypatch.setenv("CORS_ORIGINS", raw)
    settings = Settings(JWT_SECRET="test", _env_file=None)  # type: ignore[call-arg]
    assert settings.CORS_ORIGINS == expected
