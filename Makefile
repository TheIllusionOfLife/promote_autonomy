.PHONY: help dev test lint format clean install

help:
	@echo "Promote Autonomy - Development Commands"
	@echo ""
	@echo "Available commands:"
	@echo "  make install    - Install all dependencies for all services"
	@echo "  make dev        - Start all services in development mode"
	@echo "  make test       - Run tests for all services"
	@echo "  make lint       - Run linters for all services"
	@echo "  make format     - Format code for all services"
	@echo "  make clean      - Clean build artifacts and caches"

install:
	@echo "Installing dependencies..."
	cd shared && uv sync
	cd strategy-agent && uv sync
	cd creative-agent && uv sync
	cd frontend && pnpm install

dev:
	@echo "Starting development environment..."
	@echo "Start Firebase emulators in one terminal: firebase emulators:start"
	@echo "Start Strategy Agent: cd strategy-agent && uv run uvicorn app.main:app --reload --port 8000"
	@echo "Start Creative Agent: cd creative-agent && uv run uvicorn app.main:app --reload --port 8001"
	@echo "Start Frontend: cd frontend && pnpm dev"

test:
	@echo "Running tests..."
	cd shared && uv run pytest
	cd strategy-agent && uv run pytest
	cd creative-agent && uv run pytest
	cd frontend && pnpm test

lint:
	@echo "Running linters..."
	cd shared && uv run ruff check .
	cd strategy-agent && uv run ruff check . && uv run mypy app/
	cd creative-agent && uv run ruff check . && uv run mypy app/
	cd frontend && pnpm lint

format:
	@echo "Formatting code..."
	cd shared && uv run black . && uv run ruff check . --fix
	cd strategy-agent && uv run black . && uv run ruff check . --fix
	cd creative-agent && uv run black . && uv run ruff check . --fix
	cd frontend && pnpm format

clean:
	@echo "Cleaning build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".next" -exec rm -rf {} + 2>/dev/null || true
