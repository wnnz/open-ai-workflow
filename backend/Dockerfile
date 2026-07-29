FROM python:3.12-slim AS base
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY pyproject.toml ./
RUN pip install --no-cache-dir .
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic
RUN useradd --create-home --uid 10001 app \
    && mkdir -p /data/files \
    && chown -R app:app /app /data/files
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
