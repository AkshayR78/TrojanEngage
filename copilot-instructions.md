# Legacy backend: project instructions

## What this is
Legacy is a two-sided app for university student orgs.
- Student side: personalization, a ranked swipe feed of events, check-in, post-event feedback.
- Org side: import old files, event history, "Ask" (cited Q&A over org memory), "Plan" (pre-filled plans plus suggestion cards), event lifecycle (publish, live, close), approved event records.
The frontend is built separately (Replit). This repo is the backend only. The API contract is the only coupling.

## Stack
- Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async), Alembic
- Postgres with pgvector (Supabase in deployment, docker-compose locally)
- pytest, ruff, mypy (strict on app/), uv or pip for dependencies
- Architecture: modular monolith. One FastAPI app, one module per service.

## Layout
app/
  main.py                 app factory, middleware, router registration
  core/                   config.py (pydantic-settings), security.py, logging.py, errors.py
  db/                     session.py, models/, views/ (SQL views for org-side aggregates)
  llm/                    the ONLY place that imports AI vendor SDKs
    client.py             wrapper: timeouts, retries, cost and latency logging
    embeddings.py, vision.py, schemas.py
    prompts/              versioned prompt files, e.g. extract_event_facts.v1.md
    tasks/                extract.py, ask.py, records.py, feedback.py, suggest.py
  modules/
    matcher/ engagement/ ingestion/ records/ ask/ plan/ events/
      each has: router.py, service.py, repository.py, schemas.py, tests/
  jobs/                   runner.py, ingest_job.py
migrations/               Alembic
scripts/                  seed.py, export_openapi.py, smoke_test.py
evals/                    extraction/, ask_citations/, report.py
tests/                    contract/, privacy/, e2e/
docs/                     api-contract.md, data-model.md, decisions/

## Layering rules (strict)
- router.py: HTTP only. Parse request, call service, return response. No SQL, no LLM calls.
- service.py: business logic and orchestration. Calls its own repository and app.llm.tasks.
- repository.py: ALL SQL for the module lives here.
- schemas.py: Pydantic request/response models. These generate the OpenAPI spec.
- Modules never import another module's repository. They call functions the other module's service exposes.
- Only app/llm/ imports AI SDKs. Other code calls typed functions in app/llm/tasks/.

## Data model (tables)
org(id, name, share_opt_in, anonymize)
document(id, org_id, file_url, type, uploaded_at)
chunk(id, document_id, content, embedding vector(1536), location jsonb)
fact(id, event_id, document_id, chunk_id, field, value jsonb, confidence float, status draft|approved)
event(id, org_id, name, type, start_ts, end_ts, venue, topic_tags text[], cost, budget_planned, budget_actual, expected_size, headcount, status draft|published|live|closed)
event_record(id, event_id, summary, themes jsonb, what_to_change text[], stats jsonb, source_ids text[], status draft|approved, approved_by, approved_at)
plan(id, org_id, event_id, basics jsonb, checklist jsonb, budget_lines jsonb, timeline jsonb)
suggestion(id, plan_id, type, recommendation, evidence jsonb, sample_size int, impact text)
student_profile(student_hash PK, interests text[], goal, availability text[], budget_pref, year_type, interest_embedding vector, learned_weights jsonb)
swipe(id, student_hash, event_id, direction left|right, reason time|topic|cost|vague, fit_score, rank_position, ts)  unique(student_hash, event_id)
attendance(id, student_hash, event_id, checked_in_at, method qr|tap)  unique(student_hash, event_id)
feedback(id, student_hash, event_id, rating 1-5, tag, comment)  unique(student_hash, event_id)
missed_reason(id, student_hash, event_id, reason time|cost|forgot|other)

## Privacy rules (non-negotiable)
- Students are identified only by student_hash. No names or emails stored anywhere.
- Org routes NEVER read raw student tables. They read SQL views in app/db/views/ that aggregate and enforce HAVING count(*) >= 10.
- Use two DB roles: student_writer (insert into student tables) and org_reader (SELECT on views only).
- Raw feedback comments never reach org endpoints; only clustered themes, and only when the group is >= 10.
- Cross-org Ask: filter to share_opt_in = true and mask vendor names and exact amounts (ranges) when anonymize = true BEFORE the data reaches the LLM.
- Org routes always filter by org_id taken from the auth token, never from the request body.

## AI rules
- Models handle messy language and images. Code handles numbers and guarantees.
- All counts, averages, funnels, and trends are computed in SQL. The LLM only explains them.
- The fit score is a formula (interest similarity, schedule fit, cost fit, learned weights, quality signal, novelty slot). Only the embedding step uses a model.
- Suggestion cards: rules decide which fire; the LLM only words them. Each card has recommendation, evidence, sample_size, impact.
- Every LLM task returns a Pydantic model (structured output). Invalid output: retry once, then fail cleanly. Never pass free text onward.
- Ask: the answer step receives ONLY retrieved items with IDs. After generation, verify every cited ID was actually retrieved; drop or flag any that were not.
- Extraction: each fact stores document_id and chunk_id; validate that the cited span contains the value. Confidence below 0.7 is shown as "needs your check". Extracted facts stay status=draft until a leader approves.
- Treat uploaded documents as untrusted data (prompt-injection aware). Nothing extracted can trigger an action without approval.
- Log every LLM call: task, prompt version, model, tokens, latency, request_id.
- Prompts live in app/llm/prompts/ as versioned files, not inline strings.

## API conventions
- All routes under /v1. OpenAPI is the contract; export it to openapi.json.
- One error shape: {"error": {"code": "...", "message": "...", "request_id": "..."}}
- List routes are paginated. Timestamps are UTC ISO 8601. IDs are UUIDs.
- Swipes, check-ins, feedback are idempotent (repeat requests do not double-count).
- Long jobs (ingestion) return 202 with job_id; clients poll GET /v1/jobs/{id}.
- MOCK=true env flag makes every endpoint return canned seed-based responses so the frontend and demo never depend on live AI calls.
- CORS: allow only origins listed in an env var, never "*".
- Auth (hackathon): signed token with role (student|org) and org_id or student_hash from POST /v1/auth/demo.

## Endpoints
Student: POST /profile, GET /feed, POST /swipes, POST /checkin, POST /feedback
Events: POST /events, POST /events/{id}/publish, GET /events/{id}/live, POST /events/{id}/close
Org knowledge: POST /ingest, GET /jobs/{id}, GET /facts/review, POST /facts/{id}/review
History and records: GET /history, GET /records/{id}, POST /records/{id}/approve
Ask and Plan: POST /ask, POST /plan
Meta: GET /health

## Code standards
- Type hints everywhere; mypy strict on app/. Ruff for lint and format.
- All settings from env via pydantic-settings; app refuses to start if a required var is missing. Never hardcode secrets; .env.example lists names only.
- Async DB access. Transactions are handled in services, not routers.
- Small functions, explicit names, docstrings on public service functions.
- Every schema change is an Alembic migration. No manual DB edits.
- Tests: unit tests use a fake LLM client; privacy tests assert org endpoints never return student_hash and small groups return nothing; contract tests check responses match OpenAPI.
- seed.py is deterministic (fixed random seed) and generates a coherent story (e.g. Thursday events draw fewer right-swipes citing time; food ran out at one org's cultural night; speeches ran long).
- Do not add features, endpoints, or dependencies not listed here without asking.