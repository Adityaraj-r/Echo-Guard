from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from backend.database.mongodb import lifespan
from backend.api.routes import router
from backend.config import (
    ALLOWED_HOSTS,
    API_TITLE,
    API_VERSION,
    CORS_ORIGINS,
    IS_PRODUCTION,
    UPLOAD_DIR,
    ensure_directories,
)

app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    lifespan=lifespan,
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    openapi_url=None if IS_PRODUCTION else "/openapi.json",
)
 

if ALLOWED_HOSTS != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.get("/")
async def root():
    return {"service": "echoguard-api", "status": "ok"}

ensure_directories()
app.mount("/assets", StaticFiles(directory=str(UPLOAD_DIR)), name="assets")
app.include_router(router)
