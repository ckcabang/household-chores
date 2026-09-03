# Production image: uv-managed deps, collected static, Gunicorn.
FROM python:3.12-slim

# uv, pinned.
COPY --from=ghcr.io/astral-sh/uv:0.9.9 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    DJANGO_SETTINGS_MODULE=config.settings

WORKDIR /app

# Install dependencies first for layer caching.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY . .
RUN uv sync --locked --no-dev

# Collect static with a throwaway key so settings import cleanly at build time.
RUN SECRET_KEY=build-only DEBUG=True uv run python manage.py collectstatic --noinput

EXPOSE 8000

# Apply migrations, then serve. DATABASE_URL / ALLOWED_HOSTS / SECRET_KEY etc.
# come from the environment (see the README Deployment table).
CMD ["sh", "-c", "uv run python manage.py migrate --noinput && uv run gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3"]
