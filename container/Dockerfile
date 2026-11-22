FROM python:3.12-slim
WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock
COPY dbt ./dbt
COPY scripts/runner.py ./runner.py
WORKDIR /app/dbt
ENTRYPOINT ["python", "/app/runner.py"]
