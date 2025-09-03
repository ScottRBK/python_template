FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./
COPY README.md ./

# UV
RUN uv sync --frozen --no-install-project --no-dev

# Copy application code
COPY app ./app
COPY tests ./tests
COPY pytest.ini ./

RUN uv sync --frozen --no-dev

# Run the application
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010"] 
