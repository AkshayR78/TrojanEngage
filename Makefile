.PHONY: dev test lint typecheck migrate seed openapi

dev:
	uvicorn app.main:app --reload

test:
	pytest

lint:
	ruff check .

typecheck:
	mypy app

migrate:
	alembic upgrade head

seed:
	@echo "Seed data is not implemented in Phase 0."

openapi:
	python -c "import json; from app.main import app; open('openapi.json', 'w', encoding='utf-8').write(json.dumps(app.openapi(), indent=2) + '\n')"
