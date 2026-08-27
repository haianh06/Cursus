.PHONY: run test lint format typecheck check clean progress progress-snapshot

run:
	cd backend && uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

test:
	cd backend && pytest tests/ -v

lint:
	cd backend && ruff check src/ tests/

format:
	cd backend && ruff format src/ tests/

typecheck:
	cd backend && mypy src/

check: lint format test

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +

# Tiến độ team — xem docs/planning/v2/progress/README.md
progress:
	python scripts/progress_report.py

progress-snapshot:
	python scripts/progress_report.py --out docs/planning/v2/progress/SNAPSHOT.md
