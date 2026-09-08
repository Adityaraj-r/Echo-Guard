import hashlib
import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import redis.asyncio as redis
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, WebSocket, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.requests import Request
from starlette.responses import JSONResponse

from services.shared.config import Settings, get_settings
from services.shared.db import get_session, init_db
from services.shared.logging import configure_logging, get_logger
from services.shared.repository import ResultRepository
from services.shared.schemas import JobCreated, JobStatus

settings = get_settings()
configure_logging("api-gateway")
logger = get_logger(__name__)

app = FastAPI(title="EchoGuard API Gateway", version="1.0.0")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/token")
limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit_per_minute}/minute"])
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
Instrumentator().instrument(app).expose(app)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "rate limit exceeded"})


@app.on_event("startup")
async def startup() -> None:
    init_db()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.stream_dir.mkdir(parents=True, exist_ok=True)
    app.state.redis = redis.from_url(settings.redis_url, decode_responses=True)


@app.on_event("shutdown")
async def shutdown() -> None:
    await app.state.redis.aclose()


def create_token(subject: str, settings: Settings) -> str:
    expires = datetime.now(timezone.utc) + timedelta(hours=8)
    return jwt.encode({"sub": subject, "exp": expires}, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def require_user(request: Request, token: str = Depends(oauth2_scheme)) -> str:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        subject = str(payload["sub"])
    except (JWTError, KeyError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")

    session_exists = await request.app.state.redis.exists(f"session:{subject}:{token[-16:]}")
    if not session_exists:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="session expired")
    return subject


@app.post("/v1/auth/token")
async def dev_token(request: Request, username: str = "demo"):
    token = create_token(username, settings)
    await request.app.state.redis.setex(f"session:{username}:{token[-16:]}", 60 * 60 * 8, "active")
    return {"access_token": token, "token_type": "bearer"}


@app.post("/v1/audio/analyze", response_model=JobCreated)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def analyze_audio(
    request: Request,
    audio_file: UploadFile = File(...),
    user_id: str = Depends(require_user),
):
    payload = await audio_file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="empty audio file")

    audio_hash = hashlib.sha256(payload).hexdigest()
    redis_client: redis.Redis = app.state.redis
    cached_job_id = await redis_client.get(f"audio-cache:{audio_hash}")
    if cached_job_id:
        return JobCreated(job_id=cached_job_id, status=JobStatus.succeeded, cached=True)

    job_id = uuid.uuid4().hex
    safe_name = Path(audio_file.filename or "audio.wav").name
    file_path = settings.upload_dir / f"{job_id}_{safe_name}"
    file_path.write_bytes(payload)

    with get_session() as session:
        ResultRepository(session).create_job(job_id, safe_name, audio_hash, str(file_path))

    await redis_client.xadd(
        settings.audio_jobs_stream,
        {"job_id": job_id, "user_id": user_id, "retry_count": "0"},
    )
    logger.info("job_enqueued", job_id=job_id, filename=safe_name, audio_hash=audio_hash)
    return JobCreated(job_id=job_id, status=JobStatus.queued)


@app.get("/v1/results/{job_id}")
async def get_result(job_id: str, user_id: str = Depends(require_user)):
    with get_session() as session:
        job = ResultRepository(session).get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="job not found")
        return ResultRepository(session).to_result(job)


@app.websocket("/v1/audio/stream")
async def stream_audio(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        subject = str(payload["sub"])
        redis_client: redis.Redis = app.state.redis
        session_exists = await redis_client.exists(f"session:{subject}:{token[-16:]}")
        if not session_exists:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except (JWTError, KeyError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    job_id = uuid.uuid4().hex
    chunks: list[bytes] = []
    started = time.monotonic()

    try:
        while True:
            message = await websocket.receive()
            if "bytes" in message and message["bytes"]:
                chunks.append(message["bytes"])
                await websocket.send_json({"job_id": job_id, "status": "chunk_received", "chunks": len(chunks)})
            elif message.get("text") == "finish":
                audio_bytes = b"".join(chunks)
                audio_hash = hashlib.sha256(audio_bytes).hexdigest()
                file_path = settings.stream_dir / f"{job_id}.wav"
                file_path.write_bytes(audio_bytes)
                with get_session() as session:
                    ResultRepository(session).create_job(job_id, "stream.wav", audio_hash, str(file_path))
                await redis_client.xadd(settings.audio_jobs_stream, {"job_id": job_id, "user_id": subject, "retry_count": "0"})
                await websocket.send_json({"job_id": job_id, "status": "queued", "latency_ms": int((time.monotonic() - started) * 1000)})
                return
    except Exception as exc:
        logger.warning("stream_closed", job_id=job_id, error=str(exc))
