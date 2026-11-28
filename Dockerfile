FROM python:3.12-slim

# Install uv by copying its binary from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# 1. Dependencies first: this layer is cached as long as they don't change
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

# 2. Then the code
COPY src ./src
RUN uv sync --frozen --no-dev

EXPOSE 8000
CMD ["uv", "run", "--no-sync", "fastapi", "run", "src/belib_forecast/api.py", "--host", "0.0.0.0", "--port", "8000"]