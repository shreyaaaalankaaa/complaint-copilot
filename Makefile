# Convenience targets. `make demo` is the one-command path for a reviewer.
.PHONY: demo api ui seed test clean

demo:
	docker compose up -d db
	cd backend && python -m app.seed
	@echo "Now run 'make api' and 'make ui' in two terminals."

api:
	cd backend && uvicorn app.main:app --reload --port 8000

ui:
	cd frontend && npm run dev

seed:
	cd backend && python -m app.seed

sample-data:
	python scripts/make_sample_data.py

test:
	cd backend && pytest -q

clean:
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
	rm -f backend/*.db
