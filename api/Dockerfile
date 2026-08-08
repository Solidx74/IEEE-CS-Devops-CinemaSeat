FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN python -m venv /opt/venv
COPY pyproject.toml /app/pyproject.toml
WORKDIR /app
COPY app /app/app
RUN pip install --no-cache-dir .

FROM base AS test
RUN pip install --no-cache-dir ".[test]"
COPY alembic.ini /app/alembic.ini
COPY migrations /app/migrations
COPY tests /app/tests
CMD ["pytest", "-q"]

FROM base AS runtime
COPY alembic.ini /app/alembic.ini
COPY migrations /app/migrations
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh && useradd --create-home --uid 10001 app && chown -R app:app /app

USER app
EXPOSE 8000
ENTRYPOINT ["/app/docker-entrypoint.sh"]
