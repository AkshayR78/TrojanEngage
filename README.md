# TrojanEngage API

Backend scaffold and initial API slices for the TrojanEngage modular monolith.

## Local setup (five commands)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`; its health endpoint is
`GET /v1/health`. Browse all registered endpoints in Swagger UI at
`http://localhost:8000/docs`; the OpenAPI JSON is at
`http://localhost:8000/openapi.json`. `make openapi` exports the schema to
`openapi.json`. Replace the example `JWT_SECRET` before using this scaffold
outside local development. `MOCK=true` is the development default. A local
PostgreSQL database is required for database-backed features; configure
`DATABASE_URL` in `.env`.

See the [API contract](docs/api-contract.md) for request/response examples and
the current endpoint list.

## Development commands

The Makefile provides `dev`, `test`, `lint`, `typecheck`, `migrate`, `seed`, and
`openapi`; seeding is intentionally a Phase 0 placeholder.

## GitHub

GitHub setup is deferred while backend functionality is being built. Do not
commit the `.env` file; it is ignored by Git.
