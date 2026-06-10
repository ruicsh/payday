.PHONY: lint format test check run clean

lint:
	ruff check payday/

format:
	ruff format payday/

test:
	python3 -m unittest discover -v -s payday/tests

run:
	python3 -m payday

check: lint format test
	@echo "All checks passed."

clean:
	find payday -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find payday -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
