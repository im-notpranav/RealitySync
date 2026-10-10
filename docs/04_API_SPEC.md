# 04 — API Specification

**Base URL:** `/api/v1` for REST; `/health`, `/health/ready`, `/ws`, `/openapi.json`, `/docs` are at the server root · **Format:** JSON (UTF-8) · **Time:** ISO 8601 UTC (`2026-10-08T10:15:00Z`) · **IDs:** UUID v4 strings
**OpenAPI:** served at `/openapi.json`, docs at `/docs`. This document is the contract; the generated schema MUST match it.

---

## 1. Conventions

### 1.1 Authentication
| Method | Header | Used by |
|--------|--------|---------|
| Bearer JWT | `Authorization: Bearer <access_token>` | All endpoints except `/auth/login`, `/auth/refresh`, `/health*`, `/ws` (ticket) |
| API key | `X-API-Key: rs_live_…` | `POST /ingest/events` only (alternative to admin JWT) |

Role requirement is shown per endpoint: `viewer` < `analyst` < `admin` (higher roles include lower).

### 1.2 Pagination
Query: `page` (default 1), `page_size` (default 25, max 100), optional `sort` (`field` or `-field`).
```json
{ "items": [ … ], "page": 1, "page_size": 25, "total": 134 }
```

### 1.3 Error envelope (all non-2xx)
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [ { "field": "page_size", "message": "must be ≤ 100" } ],
    "request_id": "4f0c2a5e-…"
  }
}
```
| HTTP | `code` | When |
|------|--------|------|
| 400 | `BAD_REQUEST` | Malformed JSON / semantic issue |
| 401 | `UNAUTHENTICATED` | Missing/expired/invalid token |
| 401 | `INVALID_CREDENTIALS` | Wrong email/password |
| 403 | `FORBIDDEN` | Role lacks permission |
| 404 | `NOT_FOUND` | Resource missing |
| 409 | `CONFLICT` | Unique violation, illegal state transition |
| 413 | `PAYLOAD_TOO_LARGE` | Batch > 500 events |
| 422 | `VALIDATION_ERROR` | Pydantic validation failure |
| 422 | `NO_INCIDENT` | `churn` investigation but the entity has no recorded churn/cancellation (§17.3) |
| 422 | `TOO_MANY_CHECKPOINTS` | Investigation window would need > 1,000 checkpoints (§17.3) |
| 429 | `RATE_LIMITED` | Too many requests (`Retry-After` header) |
| 500 | `INTERNAL_ERROR` | Unhandled error (no internals leaked) |
| 503 | `SERVICE_UNAVAILABLE` | Readiness failed / dependency down |

### 1.4 Common enums
- `severity`: `low | medium | high | critical`
- `finding_status`: `open | acknowledged | resolved | false_positive | auto_resolved`
- `link_status`: `auto_matched | needs_review | confirmed | rejected`
- `system_key`: `crm | billing | support`
- `record_type`: `account | subscription | invoice | ticket`
- `role`: `admin | analyst | viewer`
- `alert_type`: `finding_created | finding_escalated | finding_resolved | link_needs_review | risk_threshold_crossed`
- `rule_category`: `field_conflict | logic | temporal | structural | missing_evidence`
- `risk_level`: `low | watch | warning | critical`
- `expectation_outcome`: `pending | cannot_assess` (an `unconfirmed` expectation is a finding)
- `investigation_status`: `queued | running | completed | failed`
- `investigation_outcome`: `crossed | never_crossed`

### 1.5 Validation rules (global)
Strings trimmed; max length 255 unless stated; emails RFC-valid; unknown JSON fields rejected (`extra="forbid"`) — **except inside ingest `payload`**, where unknown keys are stored raw and ignored by normalization; UUID path params validated; dates must include a timezone (naive → `422 VALIDATION_ERROR`).

**Route order note:** static paths such as `/findings/export.csv` and `/findings/bulk` MUST be registered before `/findings/{id}`.

---

## 2. Auth

### POST `/auth/login` — public
Request
```json
{ "email": "admin@realitysync.dev", "password": "S3cure-pass!" }
```
Response `200` (sets `refresh_token` httpOnly cookie, path `/api/v1/auth`)
```json
{
  "access_token": "eyJhbGciOi…",
  "token_type": "bearer",
  "expires_in": 900,
  "user": { "id": "7c1e…", "email": "admin@realitysync.dev", "full_name": "Pranav", "role": "admin" }
}
```
Errors: `401 INVALID_CREDENTIALS`, `429 RATE_LIMITED`, `422`.

### POST `/auth/refresh` — cookie + header `X-Requested-With: fetch`
Response `200`: same shape as login (new access token; refresh cookie rotated). Errors: `401 UNAUTHENTICATED` (missing/reused/expired).

### POST `/auth/logout` — any authenticated
Revokes refresh token family, clears cookie. `204`.

### GET `/auth/me` — viewer
`200`: user object `{ id, email, full_name, role, is_active, created_at }`.

### POST `/auth/change-password` — viewer
Request `{ "current_password": "…", "new_password": "Min12chars!pass" }` (new ≥ 12 chars). `204`; revokes the user's other refresh-token families; audit entry `user.password_change`. Errors: `401 INVALID_CREDENTIALS` (wrong current password), `422`. Rate limit as login.

### POST `/auth/ws-ticket` — viewer
Response `200`: `{ "ticket": "wst_9f3b…", "expires_in": 60 }` (single use).

---

## 3. Users (admin)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/users` | Paginated list; filters `role`, `is_active`, `q` |
| POST | `/users` | Create user |
| PATCH | `/users/{id}` | Update `full_name`, `role`, `is_active`, `password` |
| GET | `/api-keys` | List API keys (never returns secrets) |
| POST | `/api-keys` | Create key; secret shown **once** |
| DELETE | `/api-keys/{id}` | Revoke |

POST `/users` request
```json
{ "email": "riya@company.com", "full_name": "Riya Sharma", "role": "analyst", "password": "Min12chars!pass" }
```
Validation: password ≥ 12 chars; email unique (`409 CONFLICT`). Response `201`: user object.

POST `/api-keys` request `{ "name": "simulator", "source_system": "crm" | null }` → `201`
```json
{ "id": "…", "name": "simulator", "key": "rs_live_3kP9…(shown once)", "created_at": "…" }
```

---

## 4. Source systems

### GET `/source-systems` — viewer
```json
{ "items": [
  { "id": "…", "key": "billing", "name": "Billing", "is_active": true,
    "reliability_weight": 0.9,
    "field_authority": { "status": 0.95, "plan": 0.95, "amount": 1.0, "email": 0.6 },
    "record_counts": { "account": 500, "subscription": 480, "invoice": 5120, "ticket": 0 },
    "last_event_at": "2026-10-08T10:14:59Z" } ] }
```

### PATCH `/source-systems/{id}` — admin
Request (any subset): `{ "is_active": true, "reliability_weight": 0.8, "field_authority": { "email": 0.7 } }`. Values ∈ [0,1]. `200` updated object.

---

## 5. Ingest

### POST `/ingest/events` — admin JWT or `X-API-Key`
Request
```json
{
  "events": [
    {
      "source": "crm",
      "record_type": "account",
      "external_id": "C-1042",
      "event_type": "upsert",
      "source_updated_at": "2026-10-08T09:58:00Z",
      "idempotency_key": null,
      "payload": {
        "name": "Jon Smith", "email": "Jon.Smith@Example.com", "phone": "098765 43210",
        "status": "Customer", "plan": "Pro", "company": "Acme Pvt Ltd",
        "created_at": "2025-11-02T10:00:00Z"
      }
    },
    {
      "source": "billing",
      "record_type": "subscription",
      "external_id": "SUB-7781",
      "parent_external_id": "B-5521",
      "event_type": "upsert",
      "source_updated_at": "2026-10-08T09:59:00Z",
      "payload": { "plan": "pro", "status": "canceled", "amount": "1299.00", "currency": "INR",
                   "started_at": "2025-11-02T10:00:00Z", "cancelled_at": "2026-08-02T10:15:00Z" }
    }
  ]
}
```
Validation: 1–500 events; idempotency key computed per 03 §M1 when `idempotency_key` is null; `source` must exist and be active; if an API key is bound to a system, `source` must equal it; `payload` object ≤ 16 KB; required payload fields per `record_type` (see §5.1); `parent_external_id` required for `subscription|invoice|ticket`.

Response `202`
```json
{ "accepted": 2, "duplicates": 0, "rejected": [], "batch_id": "b5d1…" }
```
Partial rejection example: `"rejected": [ { "index": 3, "code": "VALIDATION_ERROR", "message": "payload.email is not a valid email" } ]` (valid events are still accepted).
Errors: `401`, `403`, `413 PAYLOAD_TOO_LARGE`, `422`.

#### 5.1 Required payload fields
| record_type | Required | Optional |
|-------------|----------|----------|
| account | `name`, `created_at` | `email`, `phone`, `status`, `plan`, `company`, `external_refs{}` |
| subscription | `plan`, `status`, `started_at` | `amount`, `currency`, `cancelled_at`, `quantity` |
| invoice | `amount`, `currency`, `status`, `issued_at` | `paid_at`, `due_at`, `subscription_external_id` |
| ticket | `subject`, `status`, `opened_at` | `closed_at`, `priority` (`low`/`normal`/`high`/`urgent` or aliases, 03 §M2), `first_response_at` |

`source_updated_at` is the **recorded time** of the change in the source system; the Time Machine replays history on it (FR-TMX-001). Senders must not backdate it to a business effective date.

### GET `/ingest/events` — admin
Filters: `status`, `source`, `from`, `to`. Returns paginated `{ id, source, record_type, external_id, status, attempts, error, received_at, processed_at }`.

### POST `/ingest/events/{id}/retry` — admin
Sets `failed → pending`. `202`. `409` if not failed.

---

## 6. Entities, records, links

### GET `/entities` — viewer
Filters: `q` (name/email), `health` (`consistent|inconsistent|unknown`), `has_open_findings` (bool), `system` (entities having records in that system), `min_findings`, `risk_level` (repeatable), `sort` (`-open_findings_count`, `canonical_name`, `-updated_at`, `-risk_score`).
```json
{ "items": [ {
  "id": "e1a2…", "canonical_name": "Jonathan Smith", "canonical_email": "jon.smith@example.com",
  "health": "inconsistent", "open_findings_count": 2, "highest_severity": "high",
  "risk": { "score": 0.696, "level": "warning", "confidence": 1.0 },
  "systems": ["crm","billing","support"], "updated_at": "2026-10-08T09:59:01Z" } ],
  "page": 1, "page_size": 25, "total": 500 }
```

### GET `/entities/{id}` — viewer
```json
{
  "id": "e1a2…", "canonical_name": "Jonathan Smith", "canonical_email": "jon.smith@example.com",
  "health": "inconsistent",
  "records": [
    { "link_id": "…", "link_status": "auto_matched", "match_confidence": 0.97,
      "match_features": { "email_exact": 1, "phone_exact": 1, "name_sim": 0.88 },
      "record": { "id": "…", "system": "crm", "type": "account", "external_id": "C-1042",
                  "normalized": { "name": "jonathan smith", "email": "jon.smith@example.com", "status": "active" },
                  "payload": { "name": "Jon Smith", "status": "Customer" },
                  "source_updated_at": "2026-10-08T09:58:00Z", "version": 4 } } ],
  "children": { "subscriptions": [ … ], "invoices": [ … ], "tickets": [ … ] },
  "open_findings": [ { "id": "…", "rule_key": "R004", "severity": "high", "confidence": 0.829, "status": "open", "title": "CRM active, billing cancelled" } ],
  "risk": { "…": "RiskAssessment (§17.2)" },
  "expectations": [ { "rule_key": "R016", "outcome": "pending", "trigger_record_id": "…", "expected": "invoice.paid_at",
                      "system": "billing", "deadline": "2026-10-20T00:00:00Z", "feed_watermark": "2026-10-08T09:59:00Z" } ]
}
```
`risk` is the stored live assessment (`null` before the first detection). `expectations` lists `pending` and `cannot_assess` expectations, computed on request from the live context (never stored; FR-MEV-006).
Errors: `404`.

### GET `/entities/{id}/as-of?at=<ISO8601>` — viewer
Time Machine view (§17.1).

### GET `/entities/{id}/risk-events` — viewer
Paginated risk level changes, newest first: `{ "items": [ { "from_level": "watch", "to_level": "warning", "score": 0.696, "confidence": 1.0, "at": "…" } ], … }`.

### GET `/entities/{id}/timeline` — viewer
Chronological list of record versions across systems: `{ "items": [ { "at": "…", "system": "billing", "record_type": "subscription", "external_id": "SUB-7781", "changed_fields": ["status"], "summary": "status: active → cancelled", "out_of_order": false } ] }` (paginated).

### GET `/links` — analyst
Link review queue. Filters: `status` (default `needs_review`), `min_confidence`. Returns links with both sides' normalized fields for side-by-side compare.

### POST `/links/{id}/confirm` — analyst
Body `{ "note": "same person, verified" }` (optional). `200` link. `409` if already decided.

### POST `/links/{id}/reject` — analyst
Body `{ "note": "different company" }`. `200` link.

### GET `/records` — viewer
Filters: `system`, `type`, `external_id`, `entity_id`, `is_deleted`. `GET /records/{id}` returns record + versions list.

---

## 7. Findings

### GET `/findings` — viewer
Filters: `status` (repeatable), `severity` (repeatable), `rule_key`, `system`, `entity_id`, `min_confidence`, `from`, `to`, `q` (title or entity name), `breached` (bool). Sort: `-priority_score` (default), `-last_detected_at`, `-first_detected_at`, `-confidence`, `severity`.
```json
{ "items": [ {
  "id": "f9a1…", "entity_id": "e1a2…", "entity_name": "Jonathan Smith",
  "rule_key": "R004", "title": "CRM active, billing cancelled",
  "severity": "high", "status": "open", "confidence": 0.829, "priority_score": 2.487,
  "systems": ["crm","billing"], "first_detected_at": "…", "last_detected_at": "…",
  "reopen_count": 0, "sla_breached": false, "has_explanation": true } ],
  "page": 1, "page_size": 25, "total": 62 }
```

### GET `/findings/{id}` — viewer
```json
{
  "id": "f9a1…", "entity_id": "e1a2…", "entity_name": "Jonathan Smith",
  "rule": { "key": "R004", "name": "CRM active, billing cancelled", "category": "logic" },
  "severity": "high", "status": "open",
  "confidence": 0.829,
  "confidence_breakdown": { "link": 0.97, "rule": 0.95, "evidence": 0.5, "recency": 1.0 },
  "priority_score": 2.487,
  "evidence": { "rule": { "key": "R004", "version": 1 }, "records": [ … ], "fields": [ { "field": "status", "values": { "crm": "active", "billing": "cancelled" } } ], "timestamps": { "billing.cancelled_at": "2026-08-02T10:15:00Z" }, "suggested_authority": { "field": "status", "likely_correct": "billing", "reason": "…" },
                "trail": { "facts": [ … ], "inferences": [ … ], "conclusion": { "kind": "finding", "rule_key": "R004", "risk": "high", "confidence": 0.829, "uses": ["i1","i2"] } } },
  "explanation": {
    "id": "…", "summary": "Billing shows this subscription was cancelled on 2 Aug 2026, but the CRM still lists the customer as active.",
    "root_cause": "The cancellation likely was not synced back to the CRM.",
    "likely_correct_system": "billing",
    "suggested_actions": ["Update CRM status to churned after confirming with the account owner."],
    "caveats": "If the customer re-subscribed through another channel, billing data may be incomplete.",
    "cited_fact_ids": ["f1","f2"],
    "model": "gemini-3.5-flash-lite", "is_fallback": false, "created_at": "…" },
  "history": [ { "at": "…", "action": "created" }, { "at": "…", "action": "acknowledged", "by": "Riya Sharma", "note": "looking into it" } ],
  "first_detected_at": "…", "last_detected_at": "…", "resolved_at": null, "reopen_count": 0
}
```
`explanation` is `null` while pending. `evidence.trail` follows 03 §M5; `cited_fact_ids` are ids from that trail (fallbacks cite every fact).

### PATCH `/findings/{id}` — analyst
Request `{ "status": "acknowledged" | "resolved" | "false_positive" | "open", "note": "optional ≤ 1000 chars" }`.
Rules: transitions per 03_MODULES §M6; `note` **required** for `false_positive`. Response `200` finding detail. Errors: `409 CONFLICT` (illegal transition, `details` lists allowed targets), `403`, `404`.

### POST `/findings/bulk` — analyst
Request `{ "ids": ["…","…"], "status": "acknowledged", "note": null }` (1–100 ids). Response `200`: `{ "updated": 2, "skipped": [ { "id": "…", "reason": "illegal_transition" } ] }`.

### POST `/findings/{id}/explain` — analyst
Regenerates the explanation (bypasses cache). `202` `{ "status": "queued" }`; result arrives via WebSocket `finding.explanation_ready`. `429` if daily budget exhausted.

### GET `/findings/export.csv` — analyst
Same filters as list; streams CSV (max 10,000 rows).

---

## 8. Alerts

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/alerts` | viewer | Paginated; filters `type`, `severity`, `unread` (bool) |
| GET | `/alerts/unread-count` | viewer | `{ "count": 7 }` |
| POST | `/alerts/{id}/read` | viewer | `204` |
| POST | `/alerts/read-all` | viewer | `204` |

Alert object
```json
{ "id": "a77c…", "type": "finding_created", "severity": "high", "title": "CRM active, billing cancelled",
  "body": "Jonathan Smith — confidence 83%", "finding_id": "f9a1…", "entity_id": "e1a2…",
  "link_id": null,
  "created_at": "…", "is_read": false }
```
Risk alert: `{ "type": "risk_threshold_crossed", "severity": "high", "title": "Risk rose to warning", "body": "Jonathan Smith — risk 0.70, confidence 100%", "finding_id": null, "entity_id": "e1a2…", "link_id": null, … }` (severity `high` for `warning`, `critical` for `critical`; 03 §M7).

---

## 9. Rules (admin for write)

### GET `/rules` — viewer
`{ "items": [ { "id": "…", "key": "R008", "name": "Invoice after cancellation", "category": "temporal", "description": "…", "severity": "high", "default_severity": "high", "is_enabled": true, "certainty": 0.95, "version": 1, "config": { "grace_days": 3 }, "config_schema": { "type": "object", "properties": { "grace_days": { "type": "integer", "minimum": 0 } } }, "open_findings": 12 } ] }`

`config_schema` is the JSON Schema of the rule's `config_model` (03 §M4); the Rules page builds its config form from it.

### PATCH `/rules/{id}` — admin
Request (any subset) `{ "is_enabled": false, "severity": "medium", "config": { "grace_days": 5 } }`. Config validated against the rule's schema (`422` if invalid keys/types). `200`. If `is_enabled`, `severity` or `config` changed, sets `detection_requested_at` on affected entities in batches of 500 (all entities with records when enabling or changing config; entities with active findings of this rule when disabling or changing severity); response includes `"reevaluation": "queued"`.

---

## 10. Dashboard (viewer)

### GET `/dashboard/summary`
```json
{
  "entities": 500, "systems": 3, "open_findings": 62, "needs_review_links": 9,
  "consistency_score": 91.4,
  "by_severity": { "low": 20, "medium": 25, "high": 15, "critical": 2 },
  "by_status": { "open": 50, "acknowledged": 12, "resolved": 31, "false_positive": 4, "auto_resolved": 18 },
  "by_system": { "crm": 40, "billing": 48, "support": 12 },
  "by_rule": [ { "rule_key": "R004", "count": 14 } ],
  "explained_share": 0.96,
  "spotlight": { "entity_id": "e1a2…", "canonical_name": "Jonathan Smith", "systems": ["crm","billing","support"], "highest_severity": "high", "top_priority_score": 2.487 },
  "ingest": { "events_per_sec": 12.4, "pending": 3, "detection_pending": 1, "avg_detect_ms": 18 },
  "generated_at": "…"
}
```
`open_findings` and `by_severity` count active findings (`open` + `acknowledged`). `consistency_score` is `null` when no entity has a known health (FR-DSH-002). `spotlight` is `null` when there are no active findings.

### GET `/dashboard/trends?range=7d|30d`
`{ "range": "7d", "points": [ { "date": "2026-10-02", "created": 12, "resolved": 9, "open_end_of_day": 55 } ] }`

---

## 11. Simulation & evaluation (admin)

### POST `/simulation/runs`
```json
{ "seed": 42, "customers": 500, "anomaly_rate": 0.08, "events_per_second": 25,
  "anomaly_types": ["status_conflict","email_mismatch","invoice_after_cancel"], "include_decoys": true,
  "external_ref_rate": 0.3, "history_days": 365, "scenario_rate": 0.05, "feed_outage": null }
```
Validation: `customers` 10–5000; `anomaly_rate` 0–0.5; `events_per_second` 1–200; `anomaly_types` subset of FR-SIM-004 (default all 18); `external_ref_rate` 0–1 (default 0.3); `history_days` 30–730 (default 365); `scenario_rate` 0–0.2 (default 0.05); `feed_outage` `crm|billing|support|null` (default `null`; 03 §M9).
Response `202`: `{ "id": "r12…", "status": "running", "seed": 42, "customers": 500 }`. `409` if another run is running.

### GET `/simulation/runs` · GET `/simulation/runs/{id}`
`{ "id": "…", "status": "running|completed|stopped|failed", "seed": 42, "config": { … }, "progress": { "events_sent": 1200, "events_total": 5400 }, "injected_issues": 40, "started_at": "…", "ended_at": null }`

### POST `/simulation/runs/{id}/drift`
Body `{ "count": 5, "anomaly_types": null }` → `202` `{ "injected": 5 }`. `409` if run not active/completed.

### POST `/simulation/runs/{id}/stop` → `200`

### GET `/simulation/runs/{id}/evaluation`
```json
{ "run_id": "r12…", "precision": 0.93, "recall": 0.88, "f1": 0.904,
  "true_positives": 35, "false_positives": 3, "false_negatives": 5, "ignored": 4,
  "matching": { "auto_precision": 0.995, "recall_auto_or_review": 0.97, "true_pairs": 1000 },
  "by_type": [ { "issue_type": "status_conflict", "injected": 8, "detected": 8, "recall": 1.0 } ],
  "misses": [ { "issue_type": "stale_sync", "ground_truth_key": "GT-0231", "expected_rule": "R015" } ],
  "false_positive_findings": [ "f…", "f…" ],
  "investigation": { "scenario_counts": { "churn_with_early_signals": 10, "churn_without_signals": 8, "signals_without_churn": 7 },
                     "lead_time_mae_hours": 9.6, "lead_time_within_1d_rate": 0.9, "detection_rate": 1.0,
                     "no_false_hindsight_rate": 1.0, "signals_without_churn_detection_rate": 0.857,
                     "outage_missing_evidence_findings": 0, "lookahead_violations": 0 },
  "computed_at": "…" }
```
`investigation` metrics are defined in 03 §M9; scenario rows are excluded from precision/recall.
Computed on demand (`POST …/evaluation` to force recompute).

### POST `/simulation/reset` — admin
Body `{ "confirm": "RESET" }`. Stops any running simulation first, then deletes all `ingest_events`, `source_records` (+ versions), `entities` (+ links), `rejected_pairs`, `findings` (+ events, explanations), `alerts` (+ reads), `entity_risk`, `risk_events`, `investigations` (+ checkpoints), `simulation_runs` (+ injected issues, ground truth, evaluations). Refused with `409` while an investigation is `queued` or `running`. Keeps users, API keys, rules, source systems and audit logs (reset itself is audited). `204`. `422` if confirmation text wrong.

---

## 12. Audit (admin)
`GET /audit-logs` — filters `actor_id`, `action`, `target_type`, `from`, `to`. Item: `{ id, actor, action, target_type, target_id, metadata, created_at }`.

## 13. Health (public)
Both at the server root (not `/api/v1`).
- `GET /health` → `200 { "status": "ok" }`
- `GET /health/ready` → `200 { "status": "ready", "db": "ok", "worker": "ok", "gemini": "configured|missing" }` or `503`. `worker` is `ok` when no pending ingest event and no detection request is older than 60 s (NFR-OBS-002).

---

## 14. WebSocket

**Endpoint:** `GET /ws?ticket=<ticket>` at the server root (upgrade). Invalid/used/expired ticket → close code `4401`. Subscribing to a topic the role may not read is ignored. **Topic permissions:** `findings`, `alerts`, `entities`, `ingest`, `investigations`, `system` → viewer+; `simulation` → admin.

### 14.1 Envelope (server → client)
```json
{ "v": 1, "id": "01J9ZK…", "type": "finding.created", "topic": "findings", "ts": "2026-10-08T10:15:01.123Z", "payload": { … } }
```
`id` is unique & monotonic (ULID) → clients de-duplicate.

### 14.2 Client → server
```json
{ "action": "subscribe",   "topics": ["findings","alerts","entities","ingest","investigations","simulation"] }
{ "action": "unsubscribe", "topics": ["ingest"] }
{ "action": "ping" }          // server replies with a `system.pong` envelope
```
Default after connect: subscribed to `findings`, `alerts`, `system`. Server heartbeat: a `system.ping` envelope every 25 s. All server messages, including heartbeats, use the §14.1 envelope.

### 14.3 Event types
| type | topic | payload |
|------|-------|---------|
| `finding.created` | findings | finding list item (see §7) |
| `finding.updated` | findings | finding list item + `changes: ["confidence","status"]` |
| `finding.resolved` | findings | `{ id, status, resolved_at, reason }` |
| `finding.explanation_ready` | findings | `{ finding_id, explanation }` |
| `alert.created` | alerts | alert object (§8) |
| `entity.updated` | entities | `{ id, health, open_findings_count, highest_severity }` |
| `link.needs_review` | entities | `{ link_id, entity_id, score }` |
| `risk.changed` | entities | `{ entity_id, score, level, confidence, previous_level }` (score change ≥ 0.05 or level change) |
| `investigation.progress` | investigations | `{ id, entity_id, status, checkpoints_done, checkpoints_total }` (every 25 checkpoints) |
| `investigation.completed` | investigations | `{ id, entity_id, status, outcome, first_detectable_at, lead_time_hours, error_code }` (also sent on `failed`) |
| `ingest.stats` | ingest | `{ events_per_sec, pending, detection_pending, avg_detect_ms }` |
| `simulation.progress` | simulation | `{ run_id, status, events_sent, events_total }` |
| `dashboard.counters` | findings | `{ open_findings, by_severity, consistency_score }` |
| `system.ping` | system | `{}` (heartbeat, every 25 s) |
| `system.pong` | system | `{}` (reply to client `ping`) |

### 14.4 Client behavior contract
1. Obtain ticket → connect → subscribe.
2. On any event: update TanStack Query caches and the live-feed store; ignore ids already seen.
3. On disconnect: reconnect with backoff 1 s, 2 s, 4 s … max 30 s; on reconnect refetch `dashboard/summary`, `alerts`, current list query.

---

## 15. Rate limits
| Scope | Limit |
|-------|-------|
| `POST /auth/login` | 5 failures / min / (IP+email) |
| `POST /ingest/events` | 60 req / min / API key (batch ≤ 500) |
| `POST /findings/{id}/explain` | 10 / min / user |
| `POST /auth/change-password` | 5 failures / min / user |
| `POST /investigations` | 10 / min / user |
| `GET /entities/{id}/as-of` | 60 / min / user |
| Others | 300 req / min / user |
Exceeded → `429` with `Retry-After`.

## 16. Versioning and change policy
- Breaking changes require `/api/v2` or an approved contract change (07_AGENT_RULES §Contract changes).
- Additive changes (new optional fields/endpoints) are allowed after updating this document in the same PR.

---

## 17. Time Machine, risk and investigations

### 17.1 GET `/entities/{id}/as-of?at=<ISO8601>` — viewer
What RealitySync could have known about the entity at `at`, from data recorded by then (03 §M13). Read-only: nothing is stored (FR-TMX-005).
Validation: `at` required, with timezone, not in the future (`422`). Errors: `404`, `422`.
```json
{
  "entity_id": "e1a2…", "at": "2026-07-02T00:00:00Z",
  "records": [
    { "link": { "status": "auto_matched", "match_confidence": 0.97 },
      "record": { "id": "…", "system": "crm", "type": "account", "external_id": "C-1042", "version": 3,
                  "recorded_at": "2026-06-30T08:00:00Z", "normalized": { "name": "jonathan smith", "status": "active" } } } ],
  "children": { "subscriptions": [ … ], "invoices": [ … ], "tickets": [ … ] },
  "not_yet_linkable": [ { "record_id": "…", "system": "support", "external_id": "S-88" } ],
  "findings": [ { "rule_key": "R016", "title": "Payment unconfirmed after due date", "severity": "medium",
                  "confidence": 0.765, "confidence_breakdown": { … }, "priority_score": 1.53,
                  "fingerprint": "…", "evidence_hash": "…", "evidence": { "…": "incl. trail" },
                  "live_finding_id": "f9a1…" } ],
  "expectations": [ { "rule_key": "R017", "outcome": "cannot_assess", "trigger_record_id": "…", "expected": "ticket.first_response_at",
                      "system": "support", "deadline": "2026-06-29T10:00:00Z", "feed_watermark": "2026-06-20T17:00:00Z" } ],
  "risk": { "…": "RiskAssessment (§17.2)" },
  "feed_watermarks": { "crm": "2026-07-01T22:10:00Z", "billing": "2026-07-01T23:55:00Z", "support": "2026-06-20T17:00:00Z" },
  "rule_set": { "rules": [ { "key": "R001", "version": 1, "enabled": true, "config": { } } ], "risk_model_version": 1,
                "match_auto": 0.85, "match_review": 0.6, "hash": "3f9c…" },
  "caveat": "Reconstructed from data recorded by 2 Jul 2026 00:00 UTC, evaluated with today's rules (rule set 3f9c…). Membership is reconstructed from current links."
}
```
- `records`/`children` contain the winning version of each visible record; deleted or not-yet-recorded records are absent (FR-TMX-001/002).
- `findings` are computed, never stored; `live_finding_id` is the live finding with the same fingerprint, if any (any status), else `null`.
- `match_auto`/`match_review` echo the configured `MATCH_AUTO`/`MATCH_REVIEW`.

### 17.2 RiskAssessment object
```json
{ "score": 0.696, "level": "warning", "confidence": 1.0, "model_version": 1, "assessed_at": "…",
  "signals": {
    "payment_delay":        { "value": 0.69, "available": true, "weight": 0.40 },
    "complaint_trend":      { "value": 1.0,  "available": true, "weight": 0.30 },
    "commercial_decline":   { "value": 0.6,  "available": true, "weight": 0.20 },
    "open_inconsistencies": { "value": 0.0,  "available": true, "weight": 0.10 } },
  "trail": { "facts": [ … ], "inferences": [ … ], "conclusion": { "kind": "risk", "risk": "warning", "score": 0.696, "confidence": 1.0, "uses": [ … ] } } }
```
`score` and `confidence` are always both present and are never combined (FR-RSK-002). Formulas: 03 §M12.

### 17.3 POST `/investigations` — analyst
```json
{ "entity_id": "e1a2…", "incident": { "kind": "churn" }, "lookback_days": 180, "warning_threshold": 0.6 }
{ "entity_id": "e1a2…", "incident": { "kind": "finding", "finding_id": "f9a1…", "at": "2026-08-20T09:00:00Z" } }
```
Validation: `lookback_days` 1–365 (default 180); `warning_threshold` 0.05–1.0 (default 0.60); for `finding`: `finding_id` must belong to the entity and `at` is required, with timezone, not in the future; for `churn`: `finding_id` and `at` must be absent.
Responses:
- `202` `{ "id": "i5…", "status": "queued", "checkpoints_total": 412, "incident_at": "2026-08-14T09:00:00Z" }` — new investigation (audited as `investigation.start`).
- `200` investigation object (§17.4) — an investigation with the same `inputs_hash` exists and is not `failed` (FR-INV-006).
Errors: `404` (entity or finding), `422 NO_INCIDENT`, `422 TOO_MANY_CHECKPOINTS`, `422 VALIDATION_ERROR`, `429`.
Runs in the background (at most 2 at a time, others wait in FIFO order; 02 §3.7); progress via WebSocket topic `investigations`.

### 17.4 GET `/investigations` · GET `/investigations/{id}` — viewer
List filters: `entity_id`, `status`, `outcome`; sort `-created_at` (default). List items omit `result`.
```json
{
  "id": "i5…", "entity_id": "e1a2…", "entity_name": "Jonathan Smith",
  "incident": { "kind": "churn", "finding_id": null, "finding_fingerprint": null, "at": "2026-08-14T09:00:00Z" },
  "lookback_days": 180, "warning_threshold": 0.6,
  "status": "completed", "progress": { "checkpoints_done": 412, "checkpoints_total": 412 },
  "inputs_hash": "…", "rule_set": { … },
  "outcome": "crossed", "first_detectable_at": "2026-07-02T00:00:00Z", "lead_time_hours": 1041.0,
  "result": { "…": "03 §M14 result (at_crossing risk + findings with trails, not_yet_linkable)" },
  "caveat": "Retrospective analysis using today's rules (rule set 3f9c…) on data as it was recorded at each moment. It shows when RealitySync could have flagged this, not that anyone should have acted. Membership is reconstructed from current links.",
  "error_code": null, "requested_by": { "id": "…", "full_name": "Riya Sharma" },
  "created_at": "…", "started_at": "…", "completed_at": "…"
}
```
`caveat` uses the templates in 03 §M14 and is present whenever `status = completed` (FR-INV-005). Errors: `404`.

### 17.5 GET `/investigations/{id}/checkpoints` — viewer
The full curve, not paginated (≤ 1,000 rows): `{ "items": [ { "at": "…", "risk_score": 0.41, "risk_level": "watch", "risk_confidence": 1.0, "finding_count": 1, "target_present": null } ] }`. `409` while `queued`.

### 17.6 GET `/investigations/{id}/export.json` — viewer
Download (`Content-Disposition: attachment`) of the §17.4 object plus `checkpoints`; `caveat` is the first key. `409` unless `completed`.
