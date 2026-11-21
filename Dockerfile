FROM python:3.12-slim AS dependencies

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py VERSION ./
COPY templates ./templates
COPY static ./static

FROM dependencies AS test
COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY tests ./tests
COPY k8s ./k8s
COPY kubernetes ./kubernetes
CMD ["python", "-m", "pytest", "-q"]

FROM dependencies AS runtime
ARG APP_VERSION=3.2.4
ENV APP_VERSION=${APP_VERSION} \
    ACEEST_DB_PATH=/data/aceest.db

LABEL org.opencontainers.image.title="ACEest Fitness & Gym" \
      org.opencontainers.image.version="${APP_VERSION}"

RUN groupadd --system app \
    && useradd --system --gid app --home-dir /app app \
    && mkdir -p /data \
    && chown app:app /data

USER app

EXPOSE 5000
VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=3)"]

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "--access-logfile", "-", "--error-logfile", "-", "app:create_app()"]
