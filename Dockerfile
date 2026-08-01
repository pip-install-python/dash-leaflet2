# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# dash-leaflet2 documentation site (run.py) — production image for
# https://leaflet.2plot.dev.
#
# The Leaflet 2 component bundle (dash_leaflet2/dash_leaflet2.js) is committed,
# so no Node/webpack build is needed: this is a pure-Python image serving the
# pre-built Dash app with gunicorn. node_modules/ is excluded via .dockerignore.
# ---------------------------------------------------------------------------
FROM python:3.12-slim

# PYTHONUNBUFFERED        -> stream logs straight to stdout (Render shows them live)
# PYTHONDONTWRITEBYTECODE -> no .pyc clutter in the image
# DASH_BACKEND=flask      -> WSGI backend served by gunicorn (not fastapi/quart/ASGI)
# PORT                    -> local default; Render overrides this at runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DASH_BACKEND=flask \
    PORT=8050

WORKDIR /app

# Install Python deps first so this layer is cached across app-code changes.
# vendor/ must come along: requirements.txt installs two docs-only packages
# from local tarballs there (dash-emoji-mart 0.0.5, flexlayout-dash 1.1.0).
COPY requirements.txt ./
COPY vendor/ ./vendor/
RUN pip install --no-cache-dir -r requirements.txt
# markdown2dash pins gunicorn<22, against the CVE-driven gunicorn>=23 floor in
# requirements.txt (CVE-2024-6827, CVE-2024-1135 — request smuggling). Its real
# dependencies are all in requirements.txt already, so it installs without its
# dependency graph. Same pair in .github/workflows/ci.yml; CI asserts the
# resolved gunicorn version inside this image.
RUN pip install --no-cache-dir --no-deps markdown2dash==0.1.2

# Copy the application. run.py resolves templates/, dash_leaflet2/, docs/,
# assets/, components/, lib/ and pages/ relative to the working directory, so it
# must run from /app (the repo root) — which it does under this WORKDIR.
COPY . .

# Documentation only; the process actually binds to $PORT (below).
EXPOSE 8050

# run:server is the Flask WSGI callable (run.py: `server = app.server`).
# Shell form so ${PORT} / ${WEB_CONCURRENCY} expand when the container starts.
CMD gunicorn run:server --bind "0.0.0.0:${PORT}" --workers "${WEB_CONCURRENCY:-2}" --threads 4 --timeout 120 --access-logfile - --error-logfile -
