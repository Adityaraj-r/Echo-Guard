import logging

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from starlette.concurrency import run_in_threadpool

from backend.config import ENABLE_DETECTION_DELETE, IS_PRODUCTION, MODEL_WEIGHTS_PATH
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
from backend.services.detection_files import cleanup_failed_upload
from backend.ml.readiness import ModelNotReadyError, get_model_readiness
from backend.utils.startup import ffmpeg_available

router = APIRouter()
logger = logging.getLogger("echoguard.api")


def error_payload(code: str, message: str, hint: str | None = None) -> dict:
    return {"success": False, "error": message, "code": code, "details": hint or message}


@router.get("/health")
async def health_check():
    model = get_model_readiness()
    ffmpeg_ready = ffmpeg_available()
    return {
        "status": "ok",
        "service": "echoguard-api",
        "mongodb": "connected" if is_database_ready() else "unavailable",
        "ffmpeg": "available" if ffmpeg_ready else "missing",
        "model_weights": "available" if MODEL_WEIGHTS_PATH.exists() else "missing",
        "model_status": model["state"],
        "model_ready": model["ready"],
        "readiness": "ready" if model["ready"] and ffmpeg_ready else "not_ready",
    }


async def _analyze_and_store(audio_file: UploadFile, is_live_recording: bool) -> dict:
    if IS_PRODUCTION and not get_model_readiness()["ready"]:
        raise ModelNotReadyError("The configured production model is not ready.")
    filename = audio_file.filename or ""
    inferred_live_recording = is_live_recording or filename.lower().startswith("live-recording")
    logger.info(
        "analysis request filename=%s content_type=%s inferred_live_recording=%s",
        filename or "(missing)",
        audio_file.content_type,
        inferred_live_recording,
    )
    saved_path = await persist_upload(audio_file)
    try:
        result = await run_in_threadpool(
            analyze_audio_file,
            saved_path,
            filename or saved_path.name,
            inferred_live_recording,
        )
    except Exception:
        cleanup_failed_upload(saved_path)
        raise
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

    payload = build_detection_document_payload(result)
    result.pop("_uploaded_audio_path", None)
    try:
        detection = await create_detection(payload)
        result["id"] = str(detection.id)
        result["uploaded_at"] = detection.uploaded_at.isoformat()
    except DatabaseUnavailable as exc:
        logger.warning("Analysis completed but history persistence was unavailable: %s", exc)
        if exc.definitely_not_saved:
            cleanup_failed_upload(saved_path, include_display=False)
        result["database_warning"] = str(exc)
    except Exception:
        logger.exception("Analysis completed but history persistence failed.")
        result["database_warning"] = "Analysis completed, but saving this result to history failed."

    return result


@router.post("/analyze")
async def analyze_audio_endpoint(audio_file: UploadFile = File(...)):
    try:
        return await _analyze_and_store(audio_file, is_live_recording=False)
    except AudioPipelineError as exc:
        raise HTTPException(
            status_code=400,
            detail=error_payload(
                "AUDIO_PROCESSING_ERROR",
                exc.message,
                "Verify the file is a valid supported audio recording." if IS_PRODUCTION else exc.details,
            ),
        ) from exc
    except ModelNotReadyError as exc:
        raise HTTPException(
            status_code=503,
            detail=error_payload("MODEL_NOT_READY", "The model is not ready to analyze audio."),
        ) from exc
    except Exception as exc:
        logger.exception("analysis failed")
        raise HTTPException(
            status_code=500,
            detail=error_payload("ANALYSIS_FAILED", "Analysis failed.", "Check server logs for details."),
        ) from exc


@router.post("/analyze/live")
async def analyze_live_audio_endpoint(audio_file: UploadFile = File(...)):
    try:
        return await _analyze_and_store(audio_file, is_live_recording=True)
    except AudioPipelineError as exc:
        raise HTTPException(
            status_code=400,
            detail=error_payload(
                "LIVE_AUDIO_PROCESSING_ERROR",
                exc.message,
                "Verify the file is a valid supported audio recording." if IS_PRODUCTION else exc.details,
            ),
        ) from exc
    except ModelNotReadyError as exc:
        raise HTTPException(
            status_code=503,
            detail=error_payload("MODEL_NOT_READY", "The model is not ready to analyze audio."),
        ) from exc
    except Exception as exc:
        logger.exception("live analysis failed")
        raise HTTPException(
            status_code=500,
            detail=error_payload("LIVE_ANALYSIS_FAILED", "Live analysis failed.", "Check server logs for details."),
        ) from exc


@router.get("/detections")
async def detections_index(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = None,
    prediction: str | None = Query(None, pattern="^(human|real|fake)$"),
):
    try:
        result = await list_detections(page=page, limit=limit, search=search, prediction=prediction)
        result["deletion_enabled"] = ENABLE_DETECTION_DELETE
        return result
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
    if not ENABLE_DETECTION_DELETE:
        raise HTTPException(
            status_code=403,
            detail=error_payload("DELETE_DISABLED", "Detection deletion is disabled in this deployment."),
        )
    try:
        deleted = await delete_detection(detection_id)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=error_payload("DATABASE_UNAVAILABLE", str(exc))) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail=error_payload("NOT_FOUND", "Detection record was not found."))
    return {"deleted": True}
