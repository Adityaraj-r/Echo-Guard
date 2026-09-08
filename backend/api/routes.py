import logging

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from starlette.concurrency import run_in_threadpool

from backend.config import IS_PRODUCTION, MODEL_WEIGHTS_PATH
from backend.database.mongodb import is_database_ready
from backend.services.detection_repository import (
    DatabaseUnavailable,
    create_detection,
    delete_detection,
    get_detection,
    list_detections,
    serialize_detection,
)
from backend.preprocessing.audio_pipeline import AudioPipelineError, persist_upload
from backend.services.detection_service import analyze_audio_file, build_detection_document_payload
from backend.utils.startup import ffmpeg_available

router = APIRouter()
logger = logging.getLogger("echoguard.api")


def error_payload(code: str, message: str, hint: str | None = None) -> dict:
    return {"success": False, "error": message, "code": code, "details": hint or message}


@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "echoguard-api",
        "mongodb": "connected" if is_database_ready() else "unavailable",
        "ffmpeg": "available" if ffmpeg_available() else "missing",
        "model_weights": "available" if MODEL_WEIGHTS_PATH.exists() else "missing",
    }


async def _analyze_and_store(audio_file: UploadFile, is_live_recording: bool) -> dict:
    filename = audio_file.filename or ""
    inferred_live_recording = is_live_recording or filename.lower().startswith("live-recording")
    logger.info(
        "analysis request filename=%s content_type=%s inferred_live_recording=%s",
        filename or "(missing)",
        audio_file.content_type,
        inferred_live_recording,
    )
    saved_path = await persist_upload(audio_file)
    result = await run_in_threadpool(
        analyze_audio_file,
        saved_path,
        filename or saved_path.name,
        inferred_live_recording,
    )
    logger.info(
        "inference response filename=%s verdict=%s confidence=%s fake_probability=%s human_probability=%s duration=%s sample_rate=%s channels=%s",
        result.get("filename"),
        result.get("verdict"),
        result.get("confidence"),
        result.get("fake_probability"),
        result.get("human_probability"),
        result.get("metadata", {}).get("duration"),
        result.get("metadata", {}).get("sample_rate"),
        result.get("metadata", {}).get("channels"),
    )

    try:
        detection = await create_detection(build_detection_document_payload(result))
        result["id"] = str(detection.id)
        result["uploaded_at"] = detection.uploaded_at.isoformat()
    except DatabaseUnavailable as exc:
        result["database_warning"] = str(exc)

    return result


@router.post("/analyze")
async def analyze_audio_endpoint(audio_file: UploadFile = File(...)):
    try:
        return await _analyze_and_store(audio_file, is_live_recording=False)
    except AudioPipelineError as exc:
        raise HTTPException(
            status_code=400,
            detail=error_payload("AUDIO_PROCESSING_ERROR", exc.message, exc.details),
        ) from exc
    except Exception as exc:
        logger.exception("analysis failed")
        details = "Internal analysis error. Check server logs." if IS_PRODUCTION else str(exc)
        raise HTTPException(status_code=500, detail=error_payload("ANALYSIS_FAILED", "Analysis failed.", details)) from exc


@router.post("/analyze/live")
async def analyze_live_audio_endpoint(audio_file: UploadFile = File(...)):
    try:
        return await _analyze_and_store(audio_file, is_live_recording=True)
    except AudioPipelineError as exc:
        raise HTTPException(
            status_code=400,
            detail=error_payload("LIVE_AUDIO_PROCESSING_ERROR", exc.message, exc.details),
        ) from exc
    except Exception as exc:
        logger.exception("live analysis failed")
        details = "Internal live analysis error. Check server logs." if IS_PRODUCTION else str(exc)
        raise HTTPException(status_code=500, detail=error_payload("LIVE_ANALYSIS_FAILED", "Live analysis failed.", details)) from exc


@router.get("/detections")
async def detections_index(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = None,
    prediction: str | None = Query(None, pattern="^(human|real|fake)$"),
):
    try:
        return await list_detections(page=page, limit=limit, search=search, prediction=prediction)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=error_payload("DATABASE_UNAVAILABLE", str(exc))) from exc


@router.get("/detections/{detection_id}")
async def detections_show(detection_id: str):
    try:
        detection = await get_detection(detection_id)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=error_payload("DATABASE_UNAVAILABLE", str(exc))) from exc
    if not detection:
        raise HTTPException(status_code=404, detail=error_payload("NOT_FOUND", "Detection record was not found."))
    return serialize_detection(detection)


@router.delete("/detections/{detection_id}")
async def detections_delete(detection_id: str):
    try:
        deleted = await delete_detection(detection_id)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=error_payload("DATABASE_UNAVAILABLE", str(exc))) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail=error_payload("NOT_FOUND", "Detection record was not found."))
    return {"deleted": True}
