.PHONY: lint format typecheck test check run clean

lint:
	ruff check payday/

format:
	ruff format payday/

typecheck:
	pyright payday/

test:
	python3 -m unittest discover -v -s payday/tests

run:
	python3 -m payday --config $(or $(filter-out $@,$(MAKECMDGOALS)),payday.json)

%:
	@true

run-init:
	python3 -m payday --init

run-bar:
	python3 -m payday

check: lint format typecheck test
	@echo "All checks passed."

clean:
	find payday -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find payday -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
