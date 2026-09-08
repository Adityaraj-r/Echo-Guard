from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from services.shared.db import AudioJob
from services.shared.schemas import JobResult, JobStatus, Prediction


class ResultRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_job(self, job_id: str, filename: str, audio_hash: str, file_path: str) -> AudioJob:
        job = AudioJob(
            id=job_id,
            filename=filename,
            audio_hash=audio_hash,
            file_path=file_path,
            status=JobStatus.queued.value,
        )
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job

    def get_job(self, job_id: str) -> AudioJob | None:
        return self.session.get(AudioJob, job_id)

    def get_succeeded_by_hash(self, audio_hash: str) -> AudioJob | None:
        stmt = select(AudioJob).where(
            AudioJob.audio_hash == audio_hash,
            AudioJob.status == JobStatus.succeeded.value,
        ).order_by(AudioJob.updated_at.desc())
        return self.session.execute(stmt).scalars().first()

    def mark_processing(self, job_id: str) -> None:
        self._update(job_id, status=JobStatus.processing.value)

    def mark_failed(self, job_id: str, error: str) -> None:
        self._update(job_id, status=JobStatus.failed.value, error=error)

    def mark_succeeded(self, job_id: str, prediction: Prediction) -> None:
        self._update(
            job_id,
            status=JobStatus.succeeded.value,
            synthetic_probability=prediction.synthetic_probability,
            authentic_probability=prediction.authentic_probability,
            verdict=prediction.verdict,
            error=None,
        )

    def to_result(self, job: AudioJob) -> JobResult:
        prediction = None
        if job.status == JobStatus.succeeded.value:
            prediction = Prediction(
                verdict=job.verdict or "unknown",
                synthetic_probability=job.synthetic_probability or 0.0,
                authentic_probability=job.authentic_probability or 0.0,
            )
        return JobResult(
            job_id=job.id,
            status=JobStatus(job.status),
            filename=job.filename,
            audio_hash=job.audio_hash,
            prediction=prediction,
            error=job.error,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )

    def _update(self, job_id: str, **values) -> None:
        job = self.session.get(AudioJob, job_id)
        if not job:
            return
        for key, value in values.items():
            setattr(job, key, value)
        job.updated_at = datetime.now(timezone.utc)
        self.session.commit()
