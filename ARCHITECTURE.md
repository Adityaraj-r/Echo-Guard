# EchoGuard Production Architecture

## High-Level Diagram

```text
                 +--------------------+
                 |  Client / Streamlit |
                 +----------+---------+
                            |
                            v
                    +---------------+
                    | NGINX LB/TLS  |
                    +-------+-------+
                            |
                            v
              +---------------------------+
              | API Gateway - FastAPI     |
              | JWT, rate limit, uploads  |
              | WebSocket chunks, metrics |
              +------+------+-------------+
                     |      |
        cache lookup |      | enqueue job
                     v      v
               +--------+  +----------------+
               | Redis  |  | Redis Streams  |
               | cache  |  | audio_jobs     |
               +---+----+  +-------+--------+
                   |               |
                   |               v
                   |      +----------------------+
                   |      | Worker Service       |
                   |      | retry/DLQ, Librosa   |
                   |      | spectrogram tensors  |
                   |      +----------+-----------+
                   |                 |
                   |                 v
                   |      +----------------------+
                   |      | Model Service        |
                   |      | ONNX Runtime/PyTorch |
                   |      | batch + GPU support  |
                   |      +----------+-----------+
                   |                 |
                   v                 v
              +--------------------------------+
              | Result Service / PostgreSQL   |
              | metadata, predictions, logs   |
              +--------------------------------+
```

## Service Responsibilities

| Service | Responsibility | Communication |
| --- | --- | --- |
| API Gateway | Authenticates requests, rate limits users, stores uploaded audio, checks Redis cache, publishes async jobs, exposes result and WebSocket APIs. | HTTP/WebSocket in, Redis Streams out, PostgreSQL/Redis reads. |
| Audio Processing Worker | Consumes queued jobs, validates audio, creates Mel spectrogram tensors with Librosa, batches model requests, handles retries and dead-letter failures. | Redis Streams in/out, HTTP to model service, PostgreSQL/Redis writes. |
| Model Inference Service | Loads optimized model once, supports ONNX Runtime with CUDA provider when available and PyTorch fallback, exposes single and batch inference endpoints. | HTTP JSON from worker. |
| Result Service | Encapsulates persistence of metadata, predictions, status, structured logs, and result lookup. In this scaffold it is a shared repository used by gateway and worker; it can be split into an independent FastAPI service without changing contracts. | PostgreSQL plus Redis cache. |

## Async Flow

1. User uploads audio to `POST /v1/audio/analyze`.
2. Gateway authenticates JWT, rate limits, computes audio SHA-256, checks Redis cache.
3. If cached, gateway returns the known job/result immediately.
4. If new, gateway stores the upload on shared object storage or a mounted volume, inserts a `queued` row in PostgreSQL, and publishes a Redis Stream message.
5. Worker consumes from `audio_jobs`, generates the spectrogram tensor, calls the model service, writes the final result, and caches it by audio hash.
6. Client polls `GET /v1/results/{job_id}` or keeps a WebSocket connection for chunked audio analysis.

## Scaling Strategy

- API gateway is stateless; run multiple replicas behind NGINX or a cloud load balancer.
- Workers scale horizontally by increasing replicas in the Redis consumer group. Each job is processed by one worker and can be retried by another if it remains pending.
- Model service scales separately. CPU replicas handle normal traffic; GPU replicas should be scheduled on GPU nodes and receive larger batches.
- Redis and PostgreSQL are stateful infrastructure. Use managed services or clustered deployments in production.
- Audio files should move from the local shared volume in `docker-compose.yml` to object storage such as S3, GCS, or MinIO for multi-node deployments.
- Batch inference is done at the model service boundary; workers can send one or many spectrogram tensors to `/v1/predict/batch`.
- Session data and repeated audio detections are cached in Redis with TTLs, keeping application services stateless.

## Example Endpoints

- `POST /v1/auth/token` - development JWT token endpoint.
- `POST /v1/audio/analyze` - upload audio and enqueue analysis.
- `GET /v1/results/{job_id}` - fetch queued/running/succeeded/failed status.
- `WS /v1/audio/stream` - send binary audio chunks, receive per-window predictions.
- `GET /metrics` - Prometheus metrics on gateway and model service.
- `POST /v1/predict/batch` - internal model inference endpoint.
