from contextlib import asynccontextmanager

from beanie import init_beanie
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError

from backend.models.detection import Detection
from backend.config import DATABASE_NAME, MONGODB_URL, ensure_directories
from backend.utils.audio_conversion import validate_ffmpeg_or_raise
from backend.utils.startup import build_startup_diagnostics, print_startup_diagnostics

client: AsyncIOMotorClient | None = None
database_ready = False


async def init_mongodb() -> bool:
    global client, database_ready
    client = AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=3500)
    try:
        await client.admin.command("ping")
        await init_beanie(database=client[DATABASE_NAME], document_models=[Detection])
        database_ready = True
        return True
    except (ServerSelectionTimeoutError, PyMongoError) as exc:
        database_ready = False
        print(f"[startup] MongoDB unavailable: {exc}")
        return False


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
    mongo_ready = await init_mongodb()
    print_startup_diagnostics(build_startup_diagnostics(mongo_ready=mongo_ready))
    yield
    await close_mongodb()
