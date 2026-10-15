"""What the ingest loop stores as an event's error (05 §2.5: never PII)."""

from app.workers.pipeline import PipelineError
from app.workers.queue import describe_error


def test_other_exceptions_are_reduced_to_their_class_name() -> None:
    assert describe_error(ValueError("jon@example.com is invalid")) == "ValueError"


def test_pipeline_errors_keep_their_message() -> None:
    assert describe_error(PipelineError("parent record missing")) == "parent record missing"


def test_an_empty_pipeline_error_names_its_class() -> None:
    assert describe_error(PipelineError()) == "PipelineError"


def test_long_messages_are_cut() -> None:
    assert describe_error(PipelineError("x" * 2000)) == "x" * 500
