.PHONY: run test lint format typecheck check clean progress progress-snapshot

run:
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/

typecheck:
	mypy src/

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
