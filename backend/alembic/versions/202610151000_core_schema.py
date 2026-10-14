"""core_schema: every remaining table in 05 §2.3-2.23

Records and history, entities and links, rules, findings, alerts, simulation and evaluation,
risk and investigations. Source systems are created by the startup bootstrap (05 §6), not here.

Revision ID: 202610151000
Revises: 202610141000
Create Date: 2026-10-15 10:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "202610151000"
down_revision: str | Sequence[str] | None = "202610141000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "entities",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("entity_type", sa.Text(), server_default=sa.text("'customer'"), nullable=False),
        sa.Column("canonical_name", sa.Text(), nullable=False),
        sa.Column("canonical_email", sa.Text(), nullable=True),
        sa.Column("health", sa.Text(), server_default=sa.text("'unknown'"), nullable=False),
        sa.Column("open_findings_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("highest_severity", sa.Text(), nullable=True),
        sa.Column("detection_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("entity_type IN ('customer')", name=op.f("ck_entities_entity_type")),
        sa.CheckConstraint(
            "health IN ('consistent', 'inconsistent', 'unknown')", name=op.f("ck_entities_health")
        ),
        sa.CheckConstraint(
            "highest_severity IN ('low', 'medium', 'high', 'critical')",
            name=op.f("ck_entities_highest_severity"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_entities")),
    )
    op.create_index(
        "idx_entities_detection_due",
        "entities",
        ["detection_requested_at"],
        unique=False,
        postgresql_where=sa.text("detection_requested_at IS NOT NULL"),
    )
    op.create_index(
        "ix_entities_canonical_email_trgm",
        "entities",
        ["canonical_email"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"canonical_email": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_entities_canonical_name_trgm",
        "entities",
        ["canonical_name"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"canonical_name": "gin_trgm_ops"},
    )
    op.create_index("ix_entities_health", "entities", ["health"], unique=False)
    op.create_index(
        "ix_entities_open_findings_count",
        "entities",
        [sa.literal_column("open_findings_count DESC")],
        unique=False,
    )
    op.create_table(
        "source_systems",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "reliability_weight",
            sa.Numeric(precision=3, scale=2),
            server_default=sa.text("0.80"),
            nullable=False,
        ),
        sa.Column(
            "field_authority",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "status_mapping",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "key IN ('crm', 'billing', 'support')", name=op.f("ck_source_systems_key")
        ),
        sa.CheckConstraint(
            "reliability_weight >= 0 AND reliability_weight <= 1",
            name=op.f("ck_source_systems_reliability_weight"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_systems")),
        sa.UniqueConstraint("key", name=op.f("uq_source_systems_key")),
    )
    op.create_table(
        "api_keys",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("key_prefix", sa.Text(), nullable=False),
        sa.Column("key_hash", sa.Text(), nullable=False),
        sa.Column("source_system_id", sa.UUID(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name=op.f("fk_api_keys_created_by_users")
        ),
        sa.ForeignKeyConstraint(
            ["source_system_id"],
            ["source_systems.id"],
            name=op.f("fk_api_keys_source_system_id_source_systems"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_api_keys")),
        sa.UniqueConstraint("key_hash", name=op.f("uq_api_keys_key_hash")),
    )
    op.create_table(
        "entity_risk",
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column("score", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("level", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("signals", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("trail", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("model_version", sa.Integer(), nullable=False),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "level IN ('low', 'watch', 'warning', 'critical')", name=op.f("ck_entity_risk_level")
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1", name=op.f("ck_entity_risk_confidence")
        ),
        sa.CheckConstraint("score >= 0 AND score <= 1", name=op.f("ck_entity_risk_score")),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["entities.id"],
            name=op.f("fk_entity_risk_entity_id_entities"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("entity_id", name=op.f("pk_entity_risk")),
    )
    op.create_index(
        "idx_entity_risk_level",
        "entity_risk",
        ["level", sa.literal_column("score DESC")],
        unique=False,
    )
    op.create_table(
        "ingest_events",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("batch_id", sa.UUID(), nullable=False),
        sa.Column("source_system_id", sa.UUID(), nullable=False),
        sa.Column("record_type", sa.Text(), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("parent_external_id", sa.Text(), nullable=True),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "event_type IN ('upsert', 'delete')", name=op.f("ck_ingest_events_event_type")
        ),
        sa.CheckConstraint(
            "record_type IN ('account', 'subscription', 'invoice', 'ticket')",
            name=op.f("ck_ingest_events_record_type"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'processed', 'failed')",
            name=op.f("ck_ingest_events_status"),
        ),
        sa.ForeignKeyConstraint(
            ["source_system_id"],
            ["source_systems.id"],
            name=op.f("fk_ingest_events_source_system_id_source_systems"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ingest_events")),
        sa.UniqueConstraint("idempotency_key", name=op.f("uq_ingest_events_idempotency_key")),
    )
    op.create_index(
        "idx_ingest_pending",
        "ingest_events",
        ["received_at"],
        unique=False,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "idx_ingest_processing",
        "ingest_events",
        ["locked_at"],
        unique=False,
        postgresql_where=sa.text("status = 'processing'"),
    )
    op.create_index(
        "idx_ingest_status_received",
        "ingest_events",
        ["status", sa.literal_column("received_at DESC")],
        unique=False,
    )
    op.create_table(
        "risk_events",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column("from_level", sa.Text(), nullable=True),
        sa.Column("to_level", sa.Text(), nullable=False),
        sa.Column("score", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "from_level IN ('low', 'watch', 'warning', 'critical')",
            name=op.f("ck_risk_events_from_level"),
        ),
        sa.CheckConstraint(
            "to_level IN ('low', 'watch', 'warning', 'critical')",
            name=op.f("ck_risk_events_to_level"),
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["entities.id"],
            name=op.f("fk_risk_events_entity_id_entities"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_risk_events")),
    )
    op.create_index(
        "ix_risk_events_entity_at",
        "risk_events",
        ["entity_id", sa.literal_column("at DESC")],
        unique=False,
    )
    op.create_table(
        "rules",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("default_severity", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("certainty", sa.Numeric(precision=3, scale=2), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "category IN ('field_conflict', 'logic', 'temporal', 'structural', 'missing_evidence')",
            name=op.f("ck_rules_category"),
        ),
        sa.CheckConstraint(
            "default_severity IN ('low', 'medium', 'high', 'critical')",
            name=op.f("ck_rules_default_severity"),
        ),
        sa.CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')", name=op.f("ck_rules_severity")
        ),
        sa.CheckConstraint("certainty >= 0 AND certainty <= 1", name=op.f("ck_rules_certainty")),
        sa.ForeignKeyConstraint(
            ["updated_by"], ["users.id"], name=op.f("fk_rules_updated_by_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rules")),
        sa.UniqueConstraint("key", name=op.f("uq_rules_key")),
    )
    op.create_table(
        "simulation_runs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("events_sent", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("events_total", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("started_by", sa.UUID(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'stopped', 'failed')",
            name=op.f("ck_simulation_runs_status"),
        ),
        sa.ForeignKeyConstraint(
            ["started_by"], ["users.id"], name=op.f("fk_simulation_runs_started_by_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_simulation_runs")),
    )
    op.create_table(
        "source_records",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_system_id", sa.UUID(), nullable=False),
        sa.Column("record_type", sa.Text(), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("parent_external_id", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("normalized", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("record_hash", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("source_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "record_type IN ('account', 'subscription', 'invoice', 'ticket')",
            name=op.f("ck_source_records_record_type"),
        ),
        sa.ForeignKeyConstraint(
            ["source_system_id"],
            ["source_systems.id"],
            name=op.f("fk_source_records_source_system_id_source_systems"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_records")),
        sa.UniqueConstraint(
            "source_system_id",
            "record_type",
            "external_id",
            name="uq_source_records_system_type_external_id",
        ),
    )
    op.create_index(
        "ix_source_records_email_canonical",
        "source_records",
        [sa.literal_column("(normalized ->> 'email_canonical')")],
        unique=False,
    )
    op.create_index(
        "ix_source_records_name_block",
        "source_records",
        [sa.literal_column("(normalized ->> 'name_block')")],
        unique=False,
    )
    op.create_index(
        "ix_source_records_normalized",
        "source_records",
        ["normalized"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"normalized": "jsonb_path_ops"},
    )
    op.create_index(
        "ix_source_records_phone_e164",
        "source_records",
        [sa.literal_column("(normalized ->> 'phone_e164')")],
        unique=False,
    )
    op.create_index(
        "ix_source_records_system_type_parent",
        "source_records",
        ["source_system_id", "record_type", "parent_external_id"],
        unique=False,
    )
    op.create_table(
        "entity_links",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column("source_record_id", sa.UUID(), nullable=False),
        sa.Column("match_confidence", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("match_method", sa.Text(), nullable=False),
        sa.Column(
            "match_features",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("decided_by", sa.UUID(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "match_method IN ('blocking_score', 'external_ref', 'parent', 'manual')",
            name=op.f("ck_entity_links_match_method"),
        ),
        sa.CheckConstraint(
            "status IN ('auto_matched', 'needs_review', 'confirmed', 'rejected')",
            name=op.f("ck_entity_links_status"),
        ),
        sa.CheckConstraint(
            "match_confidence >= 0 AND match_confidence <= 1",
            name=op.f("ck_entity_links_match_confidence"),
        ),
        sa.ForeignKeyConstraint(
            ["decided_by"], ["users.id"], name=op.f("fk_entity_links_decided_by_users")
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["entities.id"],
            name=op.f("fk_entity_links_entity_id_entities"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_record_id"],
            ["source_records.id"],
            name=op.f("fk_entity_links_source_record_id_source_records"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_entity_links")),
        sa.UniqueConstraint("entity_id", "source_record_id", name="uq_entity_links_entity_record"),
    )
    op.create_index("ix_entity_links_entity_id", "entity_links", ["entity_id"], unique=False)
    op.create_index(
        "ix_entity_links_status_confidence",
        "entity_links",
        ["status", sa.literal_column("match_confidence DESC")],
        unique=False,
    )
    op.create_index(
        "uq_entity_links_active_record",
        "entity_links",
        ["source_record_id"],
        unique=True,
        postgresql_where=sa.text("status <> 'rejected'"),
    )
    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("simulation_run_id", sa.UUID(), nullable=False),
        sa.Column("precision", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("recall", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("f1", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("true_positives", sa.Integer(), nullable=False),
        sa.Column("false_positives", sa.Integer(), nullable=False),
        sa.Column("false_negatives", sa.Integer(), nullable=False),
        sa.Column("ignored", sa.Integer(), nullable=False),
        sa.Column(
            "matching",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "investigation",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("by_type", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("misses", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "false_positive_findings", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["simulation_run_id"],
            ["simulation_runs.id"],
            name=op.f("fk_evaluation_runs_simulation_run_id_simulation_runs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evaluation_runs")),
    )
    op.create_table(
        "findings",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column("rule_id", sa.UUID(), nullable=False),
        sa.Column("rule_key", sa.Text(), nullable=False),
        sa.Column("fingerprint", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'open'"), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("confidence_breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("priority_score", sa.Numeric(precision=5, scale=3), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("evidence_hash", sa.Text(), nullable=False),
        sa.Column("resolved_evidence_hash", sa.Text(), nullable=True),
        sa.Column("explained_evidence_hash", sa.Text(), nullable=True),
        sa.Column("systems", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("first_detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.UUID(), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("reopen_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "jsonb_typeof(evidence) = 'object'", name=op.f("ck_findings_evidence_object")
        ),
        sa.CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')", name=op.f("ck_findings_severity")
        ),
        sa.CheckConstraint(
            "status IN ('open', 'acknowledged', 'resolved', 'false_positive', 'auto_resolved')",
            name=op.f("ck_findings_status"),
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1", name=op.f("ck_findings_confidence")
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["entities.id"],
            name=op.f("fk_findings_entity_id_entities"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by"], ["users.id"], name=op.f("fk_findings_resolved_by_users")
        ),
        sa.ForeignKeyConstraint(["rule_id"], ["rules.id"], name=op.f("fk_findings_rule_id_rules")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_findings")),
        sa.UniqueConstraint("entity_id", "fingerprint", name="uq_findings_entity_fingerprint"),
    )
    op.create_index("idx_findings_created", "findings", ["first_detected_at"], unique=False)
    op.create_index("idx_findings_entity", "findings", ["entity_id"], unique=False)
    op.create_index(
        "idx_findings_needs_explanation",
        "findings",
        [sa.literal_column("priority_score DESC")],
        unique=False,
        postgresql_where=sa.text(
            "status IN ('open', 'acknowledged') AND explained_evidence_hash IS DISTINCT FROM evidence_hash"
        ),
    )
    op.create_index(
        "idx_findings_open",
        "findings",
        ["severity", sa.literal_column("last_detected_at DESC")],
        unique=False,
        postgresql_where=sa.text("status IN ('open', 'acknowledged')"),
    )
    op.create_index("idx_findings_rule_status", "findings", ["rule_key", "status"], unique=False)
    op.create_index(
        "idx_findings_status_priority",
        "findings",
        ["status", sa.literal_column("priority_score DESC")],
        unique=False,
    )
    op.create_index(
        "ix_findings_systems", "findings", ["systems"], unique=False, postgresql_using="gin"
    )
    op.create_table(
        "injected_issues",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("simulation_run_id", sa.UUID(), nullable=False),
        sa.Column("issue_type", sa.Text(), nullable=False),
        sa.Column("ground_truth_key", sa.Text(), nullable=False),
        sa.Column("expected_rule_key", sa.Text(), nullable=True),
        sa.Column(
            "acceptable_rule_keys",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column("is_decoy", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_scenario", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("system_key", sa.Text(), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "injected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "system_key IN ('crm', 'billing', 'support')",
            name=op.f("ck_injected_issues_system_key"),
        ),
        sa.CheckConstraint(
            "NOT (is_scenario AND is_decoy)", name=op.f("ck_injected_issues_scenario_not_decoy")
        ),
        sa.CheckConstraint(
            "is_scenario OR system_key IS NOT NULL",
            name=op.f("ck_injected_issues_system_key_required"),
        ),
        sa.ForeignKeyConstraint(
            ["simulation_run_id"],
            ["simulation_runs.id"],
            name=op.f("fk_injected_issues_simulation_run_id_simulation_runs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_injected_issues")),
    )
    op.create_index(
        "ix_injected_issues_ground_truth_key", "injected_issues", ["ground_truth_key"], unique=False
    )
    op.create_index(
        "ix_injected_issues_run_issue_type",
        "injected_issues",
        ["simulation_run_id", "issue_type"],
        unique=False,
    )
    op.create_table(
        "record_versions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_record_id", sa.UUID(), nullable=False),
        sa.Column("source_system_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("normalized", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "changed_fields",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("out_of_order", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["source_record_id"],
            ["source_records.id"],
            name=op.f("fk_record_versions_source_record_id_source_records"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_system_id"],
            ["source_systems.id"],
            name=op.f("fk_record_versions_source_system_id_source_systems"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_record_versions")),
        sa.UniqueConstraint(
            "source_record_id", "version", name="uq_record_versions_record_version"
        ),
    )
    op.create_index(
        "idx_versions_system_recorded",
        "record_versions",
        ["source_system_id", sa.literal_column("source_updated_at DESC")],
        unique=False,
    )
    op.create_index(
        "ix_record_versions_record_recorded",
        "record_versions",
        ["source_record_id", sa.literal_column("source_updated_at DESC")],
        unique=False,
    )
    op.create_table(
        "rejected_pairs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("record_a_id", sa.UUID(), nullable=False),
        sa.Column("record_b_id", sa.UUID(), nullable=False),
        sa.Column("rejected_by", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("record_a_id < record_b_id", name=op.f("ck_rejected_pairs_ordered")),
        sa.ForeignKeyConstraint(
            ["record_a_id"],
            ["source_records.id"],
            name=op.f("fk_rejected_pairs_record_a_id_source_records"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["record_b_id"],
            ["source_records.id"],
            name=op.f("fk_rejected_pairs_record_b_id_source_records"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["rejected_by"], ["users.id"], name=op.f("fk_rejected_pairs_rejected_by_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rejected_pairs")),
        sa.UniqueConstraint("record_a_id", "record_b_id", name="uq_rejected_pairs_pair"),
    )
    op.create_table(
        "simulation_ground_truth",
        sa.Column("simulation_run_id", sa.UUID(), nullable=False),
        sa.Column("system_key", sa.Text(), nullable=False),
        sa.Column("record_type", sa.Text(), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("ground_truth_key", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "record_type IN ('account', 'subscription', 'invoice', 'ticket')",
            name=op.f("ck_simulation_ground_truth_record_type"),
        ),
        sa.CheckConstraint(
            "system_key IN ('crm', 'billing', 'support')",
            name=op.f("ck_simulation_ground_truth_system_key"),
        ),
        sa.ForeignKeyConstraint(
            ["simulation_run_id"],
            ["simulation_runs.id"],
            name=op.f("fk_simulation_ground_truth_simulation_run_id_simulation_runs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "simulation_run_id",
            "system_key",
            "record_type",
            "external_id",
            name=op.f("pk_simulation_ground_truth"),
        ),
    )
    op.create_index(
        "ix_simulation_ground_truth_run_key",
        "simulation_ground_truth",
        ["simulation_run_id", "ground_truth_key"],
        unique=False,
    )
    op.create_table(
        "alerts",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("finding_id", sa.UUID(), nullable=True),
        sa.Column("entity_id", sa.UUID(), nullable=True),
        sa.Column("link_id", sa.UUID(), nullable=True),
        sa.Column("dedup_key", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')", name=op.f("ck_alerts_severity")
        ),
        sa.CheckConstraint(
            "type IN ('finding_created', 'finding_escalated', 'finding_resolved', 'link_needs_review', 'risk_threshold_crossed')",
            name=op.f("ck_alerts_type"),
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["entities.id"],
            name=op.f("fk_alerts_entity_id_entities"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["finding_id"],
            ["findings.id"],
            name=op.f("fk_alerts_finding_id_findings"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["link_id"],
            ["entity_links.id"],
            name=op.f("fk_alerts_link_id_entity_links"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alerts")),
    )
    op.create_index(
        "ix_alerts_created_at", "alerts", [sa.literal_column("created_at DESC")], unique=False
    )
    op.create_index(
        "ix_alerts_dedup_key_created_at",
        "alerts",
        ["dedup_key", sa.literal_column("created_at DESC")],
        unique=False,
    )
    op.create_table(
        "finding_events",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("finding_id", sa.UUID(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "data",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "action IN ('created', 'updated', 'acknowledged', 'resolved', 'false_positive', 'reopened', 'auto_resolved', 'explained')",
            name=op.f("ck_finding_events_action"),
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["users.id"], name=op.f("fk_finding_events_actor_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["finding_id"],
            ["findings.id"],
            name=op.f("fk_finding_events_finding_id_findings"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_finding_events")),
    )
    op.create_index(
        "ix_finding_events_finding_created",
        "finding_events",
        ["finding_id", "created_at"],
        unique=False,
    )
    op.create_table(
        "finding_explanations",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("finding_id", sa.UUID(), nullable=False),
        sa.Column("input_hash", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("prompt_version", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("root_cause", sa.Text(), nullable=False),
        sa.Column("likely_correct_system", sa.Text(), nullable=False),
        sa.Column("suggested_actions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("caveats", sa.Text(), nullable=True),
        sa.Column(
            "cited_fact_ids",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column("is_fallback", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("raw_response", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "likely_correct_system IN ('crm', 'billing', 'support', 'undetermined')",
            name=op.f("ck_finding_explanations_likely_correct_system"),
        ),
        sa.ForeignKeyConstraint(
            ["finding_id"],
            ["findings.id"],
            name=op.f("fk_finding_explanations_finding_id_findings"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_finding_explanations")),
    )
    op.create_index(
        "idx_explanations_cache",
        "finding_explanations",
        ["input_hash", "prompt_version", "model", sa.literal_column("created_at DESC")],
        unique=False,
        postgresql_where=sa.text("is_fallback = false"),
    )
    op.create_index(
        "ix_finding_explanations_finding_created",
        "finding_explanations",
        ["finding_id", sa.literal_column("created_at DESC")],
        unique=False,
    )
    op.create_table(
        "investigations",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column("incident_kind", sa.Text(), nullable=False),
        sa.Column("finding_id", sa.UUID(), nullable=True),
        sa.Column("finding_fingerprint", sa.Text(), nullable=True),
        sa.Column("incident_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lookback_days", sa.Integer(), nullable=False),
        sa.Column("warning_threshold", sa.Numeric(precision=3, scale=2), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'queued'"), nullable=False),
        sa.Column("inputs_hash", sa.Text(), nullable=False),
        sa.Column("rule_set", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("checkpoints_total", sa.Integer(), nullable=False),
        sa.Column("checkpoints_done", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=True),
        sa.Column("first_detectable_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lead_time_hours", sa.Numeric(precision=8, scale=1), nullable=True),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("requested_by", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "incident_kind = 'churn' OR finding_fingerprint IS NOT NULL",
            name=op.f("ck_investigations_finding_fingerprint_required"),
        ),
        sa.CheckConstraint(
            "incident_kind IN ('churn', 'finding')", name=op.f("ck_investigations_incident_kind")
        ),
        sa.CheckConstraint(
            "outcome IN ('crossed', 'never_crossed')", name=op.f("ck_investigations_outcome")
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed')",
            name=op.f("ck_investigations_status"),
        ),
        sa.CheckConstraint(
            "lookback_days >= 1 AND lookback_days <= 365",
            name=op.f("ck_investigations_lookback_days"),
        ),
        sa.CheckConstraint(
            "warning_threshold > 0 AND warning_threshold <= 1",
            name=op.f("ck_investigations_warning_threshold"),
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["entities.id"],
            name=op.f("fk_investigations_entity_id_entities"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["finding_id"],
            ["findings.id"],
            name=op.f("fk_investigations_finding_id_findings"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by"],
            ["users.id"],
            name=op.f("fk_investigations_requested_by_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_investigations")),
    )
    op.create_index(
        "ix_investigations_active_status",
        "investigations",
        ["status"],
        unique=False,
        postgresql_where=sa.text("status IN ('queued', 'running')"),
    )
    op.create_index(
        "ix_investigations_entity_created",
        "investigations",
        ["entity_id", sa.literal_column("created_at DESC")],
        unique=False,
    )
    op.create_index(
        "uq_investigations_inputs",
        "investigations",
        ["inputs_hash"],
        unique=True,
        postgresql_where=sa.text("status <> 'failed'"),
    )
    op.create_table(
        "alert_reads",
        sa.Column("alert_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "read_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["alert_id"],
            ["alerts.id"],
            name=op.f("fk_alert_reads_alert_id_alerts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_alert_reads_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("alert_id", "user_id", name=op.f("pk_alert_reads")),
    )
    op.create_index("ix_alert_reads_user_id", "alert_reads", ["user_id"], unique=False)
    op.create_table(
        "investigation_checkpoints",
        sa.Column("investigation_id", sa.UUID(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("risk_score", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("risk_level", sa.Text(), nullable=False),
        sa.Column("risk_confidence", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column(
            "finding_fingerprints",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column("target_present", sa.Boolean(), nullable=True),
        sa.CheckConstraint(
            "risk_level IN ('low', 'watch', 'warning', 'critical')",
            name=op.f("ck_investigation_checkpoints_risk_level"),
        ),
        sa.ForeignKeyConstraint(
            ["investigation_id"],
            ["investigations.id"],
            name=op.f("fk_investigation_checkpoints_investigation_id_investigations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "investigation_id", "seq", name=op.f("pk_investigation_checkpoints")
        ),
        sa.UniqueConstraint("investigation_id", "at", name="uq_investigation_checkpoints_at"),
    )


def downgrade() -> None:
    """Downgrade schema. Dropping a table drops its indexes; order follows the foreign keys."""
    for table in (
        "investigation_checkpoints",
        "alert_reads",
        "investigations",
        "finding_explanations",
        "finding_events",
        "alerts",
        "simulation_ground_truth",
        "rejected_pairs",
        "record_versions",
        "injected_issues",
        "findings",
        "evaluation_runs",
        "entity_links",
        "source_records",
        "simulation_runs",
        "rules",
        "risk_events",
        "ingest_events",
        "entity_risk",
        "api_keys",
        "source_systems",
        "entities",
    ):
        op.drop_table(table)
