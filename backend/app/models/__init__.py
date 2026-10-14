"""Importing this package registers every table on `Base.metadata` (Alembic relies on it)."""

from app.models.alert import Alert, AlertRead
from app.models.audit_log import AuditLog
from app.models.entity import Entity, EntityLink, RejectedPair
from app.models.finding import Finding, FindingEvent, FindingExplanation, Rule
from app.models.investigation import Investigation, InvestigationCheckpoint
from app.models.refresh_token import RefreshToken
from app.models.risk import EntityRisk, RiskEvent
from app.models.simulation import (
    EvaluationRun,
    InjectedIssue,
    SimulationGroundTruth,
    SimulationRun,
)
from app.models.source_record import IngestEvent, RecordVersion, SourceRecord
from app.models.source_system import ApiKey, SourceSystem
from app.models.user import User

__all__ = [
    "Alert",
    "AlertRead",
    "ApiKey",
    "AuditLog",
    "Entity",
    "EntityLink",
    "EntityRisk",
    "EvaluationRun",
    "Finding",
    "FindingEvent",
    "FindingExplanation",
    "IngestEvent",
    "InjectedIssue",
    "Investigation",
    "InvestigationCheckpoint",
    "RecordVersion",
    "RefreshToken",
    "RejectedPair",
    "RiskEvent",
    "Rule",
    "SimulationGroundTruth",
    "SimulationRun",
    "SourceRecord",
    "SourceSystem",
    "User",
]
