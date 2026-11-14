import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/trojanengage",
)
os.environ.setdefault("JWT_SECRET", "test-only-secret-that-is-at-least-32-characters")
