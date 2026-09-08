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


USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
