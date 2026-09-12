# syntax=docker/dockerfile:1.7
# Image API Django. Contexte de build : apps/api

# ---------- base ----------
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
# GDAL/GEOS/PROJ pour GeoDjango, libpq pour psycopg, dépendances WeasyPrint pour les contrats PDF
RUN apt-get update && apt-get install -y --no-install-recommends \
      gdal-bin libgdal-dev libgeos-dev libproj-dev libpq5 \
      libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libffi8 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app

# ---------- dev ----------
FROM base AS dev
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements/base.txt requirements/dev.txt requirements/
RUN pip install -r requirements/dev.txt
COPY . .
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# ---------- builder prod ----------
FROM base AS builder
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements/base.txt requirements/prod.txt requirements/
RUN pip install --prefix=/install -r requirements/prod.txt

# ---------- prod ----------
FROM base AS prod
COPY --from=builder /install /usr/local
COPY . .
RUN addgroup --system app && adduser --system --ingroup app app \
    && chown -R app:app /app
USER app
ENV DJANGO_SETTINGS_MODULE=config.settings.prod
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60"]
