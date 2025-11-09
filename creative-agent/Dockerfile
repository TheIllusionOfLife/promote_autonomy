FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set up directory structure matching local development
# This allows relative path "../shared" to resolve correctly
WORKDIR /app

# Copy shared package to maintain relative path structure
COPY shared /app/shared

# Copy creative-agent files to /app/creative-agent
COPY creative-agent /app/creative-agent

# Set working directory to creative-agent (where pyproject.toml is)
WORKDIR /app/creative-agent

# Install dependencies (now ../shared resolves to /app/shared)
RUN uv sync --frozen --no-dev

# Cloud Run uses PORT env variable
ENV PORT=8080

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
