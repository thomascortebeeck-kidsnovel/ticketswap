FROM python:3.11-slim

WORKDIR /app

# Install only the web extras - no Playwright/Chromium needed for the wizard.
COPY pyproject.toml ./
COPY ticketswap ./ticketswap
COPY web ./web

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ".[web]"

# Cloud Run injects PORT.
ENV PORT=8080
EXPOSE 8080

# Bind to 0.0.0.0 so Cloud Run can reach it.
CMD exec uvicorn web.app:app --host 0.0.0.0 --port ${PORT}
