# List available commands
default:
    @just --list

# Run tests with coverage
test:
    uv run pytest tests/ --cov --cov-report=term-missing --cov-report=html --cov-branch --cov-fail-under=80

# Type check
typecheck:
    uv run mypy . --check-untyped-defs

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

# Run: just profile "/absolute/path/to/source" "./local_dest"
profile src_path dest_path:
    uv run py-spy record -o profile.svg -- \
    python -m imageorganizer \
    -ps "{{src_path}}" \
    -pd "{{dest_path}}"