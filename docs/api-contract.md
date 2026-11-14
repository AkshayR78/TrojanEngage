# TrojanEngage API contract

This document describes the HTTP endpoints currently implemented by the API
and a proposed contract for the organization endpoints. All application
endpoints use the `/v1` prefix and JSON request/response bodies where
applicable. Proposed endpoints are not implemented and will not appear in
Swagger until their routes are added.

## Interactive API references

With the API running locally:

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- ReDoc: `http://localhost:8000/redoc`

FastAPI generates these references from the registered routes and their Pydantic
schemas.

## Implemented endpoints

| Method | Path | Authentication | Purpose |
| --- | --- | --- | --- |
| `GET` | `/v1/health` | None | Check that the API process is responding. |
| `POST` | `/v1/auth/demo` | None | Create a demo student identity and return a signed bearer token. |
| `POST` | `/v1/profile` | Student bearer token | Create or replace the authenticated student's profile. |

### `GET /v1/health`

Returns `200 OK` when the API is responding. It does not check database
connectivity.

Example response:

```json
{
  "status": "ok"
}
```

### `POST /v1/auth/demo`

Creates a new pseudonymous student identity and returns an HS256-signed JWT.
This endpoint accepts no request body. Each request creates a new identity;
keep using the returned token to access that identity's profile.

Example request:

```bash
curl -X POST http://localhost:8000/v1/auth/demo
```

Example response (`access_token` is abbreviated):

```json
{
  "access_token": "<signed-token>",
  "token_type": "bearer",
  "expires_in": 3600
}
```

The token expires after one hour. The student identity is stored in the token's
`sub` claim as a pseudonymous hash; the API does not ask for a student's name or
email.

### `POST /v1/profile`

Creates or replaces the profile associated with the student bearer token. The
student identity is taken from the token, not from the request body. The
response does not include the identity hash.

Required header:

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

Request fields:

| Field | Type | Required | Constraints |
| --- | --- | --- | --- |
| `goal` | string | Yes | 1–500 characters. |
| `interests` | string array | No | Defaults to `[]`; at most 50 entries. |
| `availability` | string array | No | Defaults to `[]`; at most 50 entries. |
| `budget_pref` | integer or `null` | No | Must be zero or greater when provided. |
| `year_type` | string or `null` | No | At most 50 characters. |

Example request:

```bash
curl -X POST http://localhost:8000/v1/profile \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d "{\"interests\":[\"music\"],\"goal\":\"Meet people\",\"availability\":[\"Thursday evening\"],\"budget_pref\":20,\"year_type\":\"undergraduate\"}"
```

Example response (`200 OK`):

```json
{
  "interests": ["music"],
  "goal": "Meet people",
  "availability": ["Thursday evening"],
  "budget_pref": 20,
  "year_type": "undergraduate"
}
```

This endpoint persists data to PostgreSQL. Run `alembic upgrade head` against a
PostgreSQL database with the pgvector extension available before using it. The
database URL is configured with `DATABASE_URL`.

## Errors and request IDs

Errors use this response shape:

```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "A bearer token is required",
    "request_id": "<request-id>"
  }
}
```

The API also returns the request ID in the `X-Request-ID` response header.
Relevant profile/authentication responses:

| Status | Code | When |
| --- | --- | --- |
| `401` | `UNAUTHORIZED` | The profile request has no token, or its token is invalid or expired. |
| `403` | `FORBIDDEN` | The profile request's token is not for a student. |
| `404` | `NOT_FOUND` | The requested route does not exist. |
| `422` | `VALIDATION_ERROR` | The request body does not match the endpoint schema. |
| `500` | `INTERNAL_SERVER_ERROR` | An unexpected server error occurs. |

## Current scope

The student feed, swipe, check-in, and feedback endpoints are not implemented
yet. The current `/v1/profile` implementation uses PostgreSQL even when
`MOCK=true`; mock behavior is not wired into this first student slice.

## Proposed organization API

The paths below are required by the project instructions, but are not
implemented yet. Their request and response shapes are an initial proposal;
they are documented here for discussion and will need to be added to the
runtime OpenAPI schema when implemented.

### Organization authentication

Organization routes require a bearer token with `role: "org"` and an `org_id`
claim. The server must take the organization scope from that claim, never from
the request body or query string. There is not yet an implemented way to obtain
an organization token; the current `/v1/auth/demo` route issues student tokens
only.

All list routes below use cursor pagination. Proposed query parameters are
`limit` (default `20`, maximum `100`) and `cursor` (opaque, optional). Proposed
list responses have the shape:

```json
{
  "items": [],
  "next_cursor": null
}
```

### Events

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/v1/events` | Create a draft event for the authenticated organization. |
| `POST` | `/v1/events/{id}/publish` | Publish an organization's draft event. |
| `GET` | `/v1/events/{id}/live` | Read event details and eligible live aggregates. |
| `POST` | `/v1/events/{id}/close` | Close a published or live event. |

Proposed `POST /v1/events` request:

```json
{
  "name": "Cultural Night",
  "type": "social",
  "start_ts": "2026-12-10T18:00:00Z",
  "end_ts": "2026-12-10T21:00:00Z",
  "venue": "Student Center",
  "topic_tags": ["culture", "food"],
  "cost": 0,
  "budget_planned": 500,
  "expected_size": 80
}
```

`name`, `type`, `start_ts`, and `end_ts` are required. Timestamps are UTC
ISO 8601. `topic_tags` defaults to an empty list; the remaining optional values
may be omitted or `null`. The server sets `org_id` from the token and creates
the event with `status: "draft"`; callers cannot set `org_id`, `headcount`, or
the event status in this request.

Create, publish, and close responses return the event's `id` and current
`status`, along with its event fields. The proposed statuses are `draft`,
`published`, `live`, and `closed`. The `/live` response includes event details
and aggregate metrics only. A metric is omitted unless its underlying group
has at least 10 students; raw student rows and student identifiers are never
returned.

The transition from `published` to `live` is not specified by the current
endpoint list. This proposal leaves `GET /live` read-only; whether the status
changes automatically based on event time remains an implementation decision.

### Ingestion and fact review

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/v1/ingest` | Queue an organization's document for ingestion. |
| `GET` | `/v1/jobs/{id}` | Poll the status of an ingestion job. |
| `GET` | `/v1/facts/review` | List extracted draft facts for review. |
| `POST` | `/v1/facts/{id}/review` | Approve a draft fact. |

Proposed `POST /v1/ingest` request:

```json
{
  "file_url": "https://storage.example.edu/org-documents/agenda.pdf",
  "type": "pdf"
}
```

`file_url` must refer to an object in configured trusted storage; the
implementation must not fetch arbitrary user-supplied network URLs. The
proposed response is `202 Accepted`:

```json
{
  "job_id": "UUID",
  "status": "queued"
}
```

`GET /v1/jobs/{id}` returns `job_id`, `status`, and, when available, a result
summary or a safe error code. Proposed job statuses are `queued`, `running`,
`succeeded`, and `failed`; clients should not receive internal stack traces.

`GET /v1/facts/review` returns paginated draft facts with `id`, `event_id`,
`field`, `value`, `confidence`, `document_id`, `chunk_id`, and `status`.
Evidence shown for review should include only the relevant source excerpt.
`POST /v1/facts/{id}/review` accepts:

```json
{
  "decision": "approve"
}
```

The initial contract supports approval only, matching the `draft` and
`approved` fact statuses in the data model. Approval returns the updated fact;
extracted facts remain drafts until explicitly approved.

### History and event records

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/v1/history` | List the organization's events and eligible aggregate history. |
| `GET` | `/v1/records/{id}` | Read an event record owned by the organization. |
| `POST` | `/v1/records/{id}/approve` | Approve a draft event record. |

`GET /v1/history` is paginated and returns event summaries and aggregate
statistics only. The record response contains `id`, `event_id`, `summary`,
`themes`, `what_to_change`, `stats`, `source_ids`, `status`, and, after
approval, `approved_by` and `approved_at`. It never returns raw feedback
comments or student identifiers. Feedback themes and other student-derived
aggregates are omitted unless the group size is at least 10.

`POST /v1/records/{id}/approve` takes no body and returns the updated record
with `status: "approved"` and its approval timestamp. The authenticated
organization must own the record's event. The individual approver identity
claim is not defined yet; it must be decided when organization authentication
is implemented.

### Ask and Plan

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/v1/ask` | Ask a question against authorized organization knowledge. |
| `POST` | `/v1/plan` | Create or update an event plan and return suggestion cards. |

Proposed `POST /v1/ask` request:

```json
{
  "question": "What should we change about the event schedule?"
}
```

The response contains an `answer` and a `citations` array with source IDs.
Every cited ID must correspond to an item actually retrieved for the answer.
Cross-organization sources are available only when `share_opt_in` is true. If
the source organization enables anonymization, vendor names and exact amounts
must be masked or converted to ranges before source content reaches the LLM.

Proposed `POST /v1/plan` request:

```json
{
  "event_id": "UUID",
  "basics": {
    "goal": "Welcome new members",
    "expected_size": 80
  }
}
```

The response contains the plan's `id`, `event_id`, `basics`, `checklist`,
`budget_lines`, and `timeline`, plus `suggestions`. Each suggestion contains
`type`, `recommendation`, `evidence`, `sample_size`, and `impact`. The event
must belong to the authenticated organization. Rule-based logic decides which
suggestions appear; an LLM may phrase them but does not calculate metrics.

### Organization privacy and errors

Organization endpoints must scope every operation by the token's `org_id`.
They must read student-derived information only through aggregate SQL views
that enforce `HAVING count(*) >= 10`; they must never query raw student tables.
Raw feedback comments are not exposed to organization endpoints.

When implemented, organization endpoints use the same error envelope and
`X-Request-ID` response header described above. Long-running ingestion uses
`202 Accepted` and a `job_id` rather than waiting for the job to finish.
