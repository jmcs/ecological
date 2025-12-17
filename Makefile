PYTHON_FILES=$(find . -name "*.py" -not -path "./.venv/*" -not -path "./build/*" -not -path "./dist/*" -not -path "./tests/*")

dist/: ${PYTHON_FILES} pyproject.toml
	uv build

.PHONY: publish
publish: dist/
	uv publish dist/*

.PHONY: test
test:
	uv run pytest --cov=ecological --cov-report=term-missing tests/

.PHONY: typecheck
typecheck:
	uv run ty check ecological/

.PHONY: lint
lint:
	uv run ruff check ecological/

.PHONY: format
format:
	uv run ruff format ecological/

.PHONY: check-all
check-all: test typecheck lint