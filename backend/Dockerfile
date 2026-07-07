FROM python:3.11.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

ARG INSTALL_DEV_DEPENDENCIES=true

COPY requirements.txt requirements-dev.txt ./

RUN groupadd --system app && useradd --system --gid app --create-home app \
    && pip install --no-cache-dir --upgrade pip \
    && if [ "$INSTALL_DEV_DEPENDENCIES" = "true" ]; then \
        pip install --no-cache-dir -r requirements-dev.txt; \
    else \
        pip install --no-cache-dir -r requirements.txt; \
    fi

COPY . .

RUN mkdir -p /app/storage \
    && chown -R app:app /app

USER app

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import os, urllib.request; req=urllib.request.Request('http://127.0.0.1:8000/api/v1/health'); enabled=os.getenv('API_KEY_ENABLED', '').lower() in {'1', 'true', 'yes', 'on'}; key=os.getenv('API_KEY'); req.add_header('X-API-Key', key) if enabled and key else None; urllib.request.urlopen(req, timeout=3)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
