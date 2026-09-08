import asyncio
import json

import httpx
import redis.asyncio as redis

from services.shared.config import get_settings
from services.shared.db import get_session, init_db
from services.shared.logging import configure_logging, get_logger
from services.shared.repository import ResultRepository
from services.shared.schemas import BatchPredictionRequest, ModelPredictionRequest, Prediction
from services.worker.audio_processing import AudioProcessor

settings = get_settings()
configure_logging("audio-worker")
logger = get_logger(__name__)


class AudioJobWorker:
    def __init__(self) -> None:
        self.redis = redis.from_url(settings.redis_url, decode_responses=True)
        self.processor = AudioProcessor(settings)

    async def start(self) -> None:
        init_db()
        await self._ensure_group()
        logger.info("worker_started", stream=settings.audio_jobs_stream, group=settings.consumer_group)
        while True:
            messages = await self.redis.xreadgroup(
                groupname=settings.consumer_group,
                consumername="worker-1",
                streams={settings.audio_jobs_stream: ">"},
                count=8,
                block=5000,
            )
            for _, entries in messages:
                await self._handle_batch(entries)

    async def _ensure_group(self) -> None:
        try:
            await self.redis.xgroup_create(settings.audio_jobs_stream, settings.consumer_group, id="0", mkstream=True)
        except redis.ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    async def _handle_batch(self, entries: list[tuple[str, dict]]) -> None:
        prepared: list[tuple[str, str, str, str]] = []
        requests: list[ModelPredictionRequest] = []

        for message_id, fields in entries:
            job_id = fields["job_id"]
            with get_session() as session:
                repo = ResultRepository(session)
                job = repo.get_job(job_id)
                if not job:
                    await self.redis.xack(settings.audio_jobs_stream, settings.consumer_group, message_id)
                    continue
                repo.mark_processing(job_id)
                try:
                    tensor = self.processor.to_mel_tensor(job.file_path)
                    requests.append(ModelPredictionRequest(job_id=job_id, spectrogram=tensor))
                    prepared.append((message_id, job_id, job.audio_hash, str(fields.get("retry_count", "0"))))
                except Exception as exc:
                    await self._fail_or_retry(message_id, fields, job_id, str(exc))

        if not requests:
            return

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{settings.model_service_url}/v1/predict/batch",
                    json=BatchPredictionRequest(items=requests).model_dump(),
                )
                response.raise_for_status()
                payload = response.json()["predictions"]

            with get_session() as session:
                repo = ResultRepository(session)
                for message_id, job_id, audio_hash, _ in prepared:
                    prediction = Prediction(**payload[job_id])
                    repo.mark_succeeded(job_id, prediction)
                    await self.redis.setex(f"audio-cache:{audio_hash}", settings.cache_ttl_seconds, job_id)
                    await self.redis.xack(settings.audio_jobs_stream, settings.consumer_group, message_id)
                    logger.info("job_succeeded", job_id=job_id, synthetic_probability=prediction.synthetic_probability)
        except Exception as exc:
            for message_id, job_id, _, retry_count in prepared:
                await self._fail_or_retry(message_id, {"job_id": job_id, "retry_count": retry_count}, job_id, str(exc))

    async def _fail_or_retry(self, message_id: str, fields: dict, job_id: str, error: str) -> None:
        retry_count = int(fields.get("retry_count", "0")) + 1
        if retry_count <= settings.max_retries:
            await self.redis.xadd(settings.audio_jobs_stream, {"job_id": job_id, "retry_count": str(retry_count)})
            logger.warning("job_requeued", job_id=job_id, retry_count=retry_count, error=error)
        else:
            with get_session() as session:
                ResultRepository(session).mark_failed(job_id, error)
            await self.redis.xadd(settings.failed_jobs_stream, {"job_id": job_id, "error": error})
            logger.error("job_failed", job_id=job_id, error=error)
        await self.redis.xack(settings.audio_jobs_stream, settings.consumer_group, message_id)


if __name__ == "__main__":
    asyncio.run(AudioJobWorker().start())
