FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    ENVIRONMENT=production \
    FFMPEG_PATH=/usr/bin \
    UPLOAD_DIR=/data/uploads \
    TEMP_AUDIO_DIR=/data/temp_audio \
    TEMP_IMAGE_DIR=/data/temp_images

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

COPY . .

RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && mkdir -p /data/uploads /data/temp_audio /data/temp_images \
    && chown -R appuser:appuser /data

USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
