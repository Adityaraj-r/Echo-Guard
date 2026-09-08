FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

COPY services ./services
COPY model_definition.py ./model_definition.py

CMD ["uvicorn", "services.gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
