# TrojanEngage API contract

This document describes the HTTP endpoints currently implemented by the API
and a proposed contract for organization endpoints that are still pending.
All application endpoints use the `/v1` prefix and JSON request/response
bodies where applicable. Pending endpoints will not appear in Swagger until
their routes are added.

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
| `POST` | `/v1/auth/demo` | None | Create a demo student or organization identity and return a signed bearer token. |
| `POST` | `/v1/profile` | Student bearer token | Create or replace the authenticated student's profile. |
| `POST` | `/v1/events` | Organization bearer token | Create a draft event for the authenticated organization. |
| `POST` | `/v1/events/{event_id}/publish` | Organization bearer token | Publish a draft event. |
| `GET` | `/v1/events/{event_id}/live` | Organization bearer token | Read a published or live event. |
| `POST` | `/v1/events/{event_id}/close` | Organization bearer token | Close a published or live event. |

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

Creates a demo identity and returns an HS256-signed JWT. With no request body
or `{"role":"student"}`, it creates a pseudonymous student identity. To create
a demo organization, send a JSON body with `role: "org"` and an
`organization_name`; the organization is persisted and its generated ID is
included in the token. Each request creates a new identity or organization.
Keep the returned token to continue using that identity.

Example request:

```bash
curl -X POST http://localhost:8000/v1/auth/demo
```

Example response (`access_token` is abbreviated):

```json
{
  "access_token": "<signed-token>",
  "token_type": "bearer",
  "expires_in": 3600,
  "role": "student",
  "org_id": null
}
```

Organization request:

```json
{
  "role": "org",
  "organization_name": "Trojan Student Org"
}
```

An organization response includes `"role":"org"` and its generated UUID in
`org_id`, for example:

```json
{
  "access_token": "<signed-token>",
  "token_type": "bearer",
  "expires_in": 3600,
  "role": "org",
  "org_id": "c1ff61c7-294c-48c4-9c2a-bdb601bb9322"
}
```

The token expires after one hour. For students, the pseudonymous hash is stored
in the token's `sub` claim; the API does not ask for a student's name or email.
For organizations, the token includes the generated `org_id`. Demo auth is for
local development and is not production authentication.

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

### Organization event lifecycle

All event routes require an organization token. The `org_id` is read from the
token and is never accepted from the request body. Event IDs are UUIDs.

#### `POST /v1/events`

Creates an event in `draft` status and returns `201 Created`.

Request fields:

| Field | Type | Required | Constraints |
| --- | --- | --- | --- |
| `name` | string | Yes | 1–200 characters. |
| `type` | string | Yes | 1–80 characters. |
| `start_ts`, `end_ts` | timestamp | Yes | UTC ISO 8601; end must be later than start. |
| `venue` | string or `null` | No | At most 255 characters. |
| `topic_tags` | string array | No | Defaults to `[]`; at most 50 entries. |
| `cost`, `budget_planned` | number or `null` | No | Must be zero or greater. |
| `expected_size` | integer or `null` | No | Must be zero or greater. |

`org_id`, `status`, `headcount`, and `budget_actual` are server-managed and
cannot be set through this endpoint.

#### `POST /v1/events/{event_id}/publish`

Changes a draft event to `published` and returns `200 OK`. Publishing an
already published event is idempotent. Other source statuses return `409
Conflict`.

#### `GET /v1/events/{event_id}/live`

Returns the event details for events in `published` or `live` status. Draft or
closed events return `409 Conflict`. Aggregate live metrics are not implemented
yet, so this initial response contains event details only.

There is not yet a route or background job that transitions an event from
`published` to `live`; the `GET` route does not change event state.

#### `POST /v1/events/{event_id}/close`

Changes a `published` or `live` event to `closed` and returns `200 OK`.
Closing an already closed event is idempotent. Draft events return
`409 Conflict`.

Event data is persisted to PostgreSQL. Apply the Alembic migrations before
using these routes. The repository scopes event lookups by both event ID and
the organization ID from the token; an event owned by another organization is
reported as `404 Not Found`.

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
| `401` | `UNAUTHORIZED` | A protected request has no token, or its token is invalid or expired. |
| `403` | `FORBIDDEN` | The token role is not allowed for the requested route. |
| `404` | `NOT_FOUND` | The route or an organization-owned resource does not exist in scope. |
| `409` | `INVALID_EVENT_STATUS` / `EVENT_NOT_LIVE` | An event lifecycle action is invalid for its current status. |
| `422` | `VALIDATION_ERROR` | The request body does not match the endpoint schema. |
| `500` | `INTERNAL_SERVER_ERROR` | An unexpected server error occurs. |

## Current scope

The student feed, swipe, check-in, and feedback endpoints are not implemented
yet. The current `/v1/profile` implementation uses PostgreSQL even when
`MOCK=true`; mock behavior is not wired into this first student slice.

## Remaining proposed organization API

The paths below are required by the project instructions, but are not
implemented yet. Their request and response shapes are an initial proposal;
they are documented here for discussion and will need to be added to the
runtime OpenAPI schema when implemented. Organization demo authentication and
the event lifecycle above are implemented.

### Organization authentication

Organization routes require a bearer token with `role: "org"` and an `org_id`
claim. The server must take the organization scope from that claim, never from
the request body or query string. `POST /v1/auth/demo` currently creates a new
demo organization when called with `role: "org"`; production organization
authentication and reuse of existing organizations are not implemented.

All list routes below use cursor pagination. Proposed query parameters are
`limit` (default `20`, maximum `100`) and `cursor` (opaque, optional). Proposed
list responses have the shape:

```json
{
  "items": [],
  "next_cursor": null
}
```

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
