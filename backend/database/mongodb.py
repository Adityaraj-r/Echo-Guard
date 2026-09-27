import asyncio
import logging
from contextlib import asynccontextmanager

from beanie import init_beanie
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient

from backend.models.detection import Detection
from backend.config import DATABASE_NAME, MONGODB_URL, ensure_directories
from backend.utils.audio_conversion import validate_ffmpeg_or_raise
from backend.utils.startup import build_startup_diagnostics, print_startup_diagnostics

logger = logging.getLogger("echoguard.database")
client: AsyncIOMotorClient | None = None
database_ready = False


async def init_mongodb() -> bool:
    global client, database_ready
    if client is None:
        client = AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=2500)
    try:
        await client.admin.command("ping")
        await init_beanie(database=client[DATABASE_NAME], document_models=[Detection])
        database_ready = True
        return True
    except Exception as exc:
        database_ready = False
        logger.warning("MongoDB initialization failed (%s).", type(exc).__name__)
        if client:
            client.close()
        client = None
        return False


def mark_database_unready() -> None:
    global client, database_ready
    database_ready = False
    if client:
        client.close()
    client = None


async def monitor_mongodb(stop_event: asyncio.Event, retry_interval: float = 10.0) -> None:
    """Keep one bounded readiness/recovery task for the application lifetime."""
    global client, database_ready
    while not stop_event.is_set():
        if database_ready and client:
            try:
                await client.admin.command("ping")
            except Exception as exc:
                logger.warning("MongoDB health check failed (%s); marking database unavailable.", type(exc).__name__)
                mark_database_unready()
        if not database_ready:
            await init_mongodb()
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=retry_interval)
        except asyncio.TimeoutError:
            continue


async def close_mongodb() -> None:
    global client, database_ready
    if client:
        client.close()
    client = None
    database_ready = False


def is_database_ready() -> bool:
    return database_ready


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_directories()
    validate_ffmpeg_or_raise()
    try:
        from backend.ml.model_inference import initialize_model

        model_ready = initialize_model()
    except Exception as exc:
        from backend.ml.readiness import set_model_readiness

        set_model_readiness("runtime_unavailable", False)
        logger.error("Model runtime is unavailable during startup (%s).", type(exc).__name__)
        model_ready = False
    mongo_ready = await init_mongodb()
    stop_mongo_monitor = asyncio.Event()
    mongo_monitor = asyncio.create_task(monitor_mongodb(stop_mongo_monitor), name="mongodb-readiness")
    diagnostics = build_startup_diagnostics(mongo_ready=mongo_ready)
    diagnostics["model_ready"] = model_ready
    print_startup_diagnostics(diagnostics)
    try:
        yield
    finally:
        stop_mongo_monitor.set()
        await mongo_monitor
        await close_mongodb()
