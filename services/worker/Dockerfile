FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends libsndfile1 && rm -rf /var/lib/apt/lists/*
COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

COPY services ./services
COPY model_definition.py ./model_definition.py

CMD ["python", "-m", "services.worker.consumer"]
