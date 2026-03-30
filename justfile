# List available commands
default:
    @just --list

# Run tests with coverage
test:
    uv run pytest tests/ --cov --cov-report=term-missing --cov-report=html --cov-branch --cov-fail-under=80

# Type check
typecheck:
    uv run mypy .

# Lint
lint:
    uv run ruff check .

# Format
format:
    uv run ruff format .

# Run all checks
check: format lint typecheck test

# Build the package
build: check
    uv build

# Clean build artifacts
clean:
    rm -rf dist/ htmlcov/ .coverage
