FROM python:3.14.10-slim AS wheel-builder
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /build
COPY requirements.lock .
RUN python -m pip wheel --no-cache-dir --wheel-dir=/wheels -r requirements.lock

FROM python:3.14.10-slim
WORKDIR /app
COPY requirements.lock .
COPY --from=wheel-builder /wheels /wheels
RUN python -m pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.lock \
    && rm -rf /wheels
COPY dbt ./dbt
COPY scripts/runner.py ./runner.py
WORKDIR /app/dbt
ENTRYPOINT ["python", "/app/runner.py"]
