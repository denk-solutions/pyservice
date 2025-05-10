
FROM python:3.13-slim AS builder

# Copy in uvx from their image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy in the app
COPY . /app
WORKDIR /app

ENV UV_LINK_MODE=copy

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock,z \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml,z \
    uv sync --locked --no-install-project --no-group dev --no-group test

# Copy the project into the image
ADD . /app

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

FROM python:3.13-slim

# Copy the environment, but not the source code
COPY --from=builder /app /app

WORKDIR /app

CMD ["/app/.venv/bin/fastapi", "run", "src/pyservice/api/server.py", "--port", "80", "--host", "0.0.0.0"]
