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

# CACHE SEMANTICS — read this before shipping a dependency upgrade. This layer
# re-runs ONLY when vendor/ or requirements.txt BYTES change. A `>=` floor can
# NEVER pull a newer release through a cache hit: a code-only commit rebuilds
# the app layers below while pip silently keeps whatever version the image was
# first built with. That has bitten this repo twice — 2.6.1 and again at 2.7.1
# — and both times the site looked fine, because a stale package degrades
# quietly rather than failing.
#
# So ship every dependency upgrade as a floor bump in requirements.txt, and
# grep the NUMBER, not the file: it also lives in run.py's LLMS_PKG_FLOOR and
# in ci.yml's asserts. The bump IS the cache bust, and the boot floor turns a
# stale image from a silent downgrade into a loud refusal to start.
#
# vendor/ must come along: requirements.txt installs dash-clerk-auth 1.0.5 from
# a local tarball there (it is vendored across the 2plot network, not on PyPI).
# dash-emoji-mart and flexlayout-dash used to live here too and now come from
# PyPI, so this is down to the single Clerk tarball.
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
