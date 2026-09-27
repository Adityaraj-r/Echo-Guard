import logging
from typing import Any

from beanie.operators import RegEx
from bson import ObjectId
from pymongo.errors import PyMongoError

from backend.database.mongodb import is_database_ready, mark_database_unready
from backend.models.detection import Detection
from backend.services.detection_files import cleanup_detection_files, detection_artifact_references

logger = logging.getLogger("echoguard.repository")


class DatabaseUnavailable(RuntimeError):
    def __init__(self, message: str, *, definitely_not_saved: bool = False):
        super().__init__(message)
        self.definitely_not_saved = definitely_not_saved


def _require_database() -> None:
    if not is_database_ready():
        raise DatabaseUnavailable(
            "MongoDB is not connected; the result was not saved to history.",
            definitely_not_saved=True,
        )


def serialize_detection(detection: Detection) -> dict[str, Any]:
    data = detection.model_dump(mode="json")
    data["id"] = str(detection.id)
    data.pop("_id", None)
    data.pop("uploaded_audio_path", None)
    return data


async def create_detection(payload: dict[str, Any]) -> Detection:
    _require_database()
    try:
        detection = Detection(**payload)
    except Exception as exc:
        raise DatabaseUnavailable(
            "The analysis completed, but its history record could not be created.",
            definitely_not_saved=True,
        ) from exc
    try:
        await detection.insert()
    except Exception as exc:
        if isinstance(exc, PyMongoError):
            mark_database_unready()
        logger.exception("Detection record insert failed.")
        raise DatabaseUnavailable("MongoDB did not confirm whether the result was saved to history.") from exc
    return detection


async def list_detections(
    page: int = 1,
    limit: int = 20,
    search: str | None = None,
    prediction: str | None = None,
) -> dict[str, Any]:
    _require_database()
    page = max(page, 1)
    limit = min(max(limit, 1), 100)

    filters = []
    if search:
        filters.append(RegEx(Detection.filename, search, "i"))
    if prediction:
        filters.append(Detection.prediction == prediction.lower())

    query = Detection.find(*filters) if filters else Detection.find()
    try:
        total = await query.count()
        items = (
            await query.sort("-uploaded_at")
            .skip((page - 1) * limit)
            .limit(limit)
            .to_list()
        )
    except PyMongoError as exc:
        mark_database_unready()
        raise DatabaseUnavailable("MongoDB is unavailable while loading detection history.") from exc

    return {
        "items": [serialize_detection(item) for item in items],
        "page": page,
        "limit": limit,
        "total": total,
    }


async def get_detection(detection_id: str) -> Detection | None:
    _require_database()
    if not ObjectId.is_valid(detection_id):
        return None
    try:
        return await Detection.get(ObjectId(detection_id))
    except PyMongoError as exc:
        mark_database_unready()
        raise DatabaseUnavailable("MongoDB is unavailable while loading the detection record.") from exc


async def delete_detection(detection_id: str) -> bool:
    detection = await get_detection(detection_id)
    if not detection:
        return False
    references = detection_artifact_references(detection)
    shared_files = False
    if references:
        for field, value in references.items():
            query = Detection.find(Detection.id != detection.id, getattr(Detection, field) == value)
            try:
                if await query.count():
                    shared_files = True
                    break
            except PyMongoError as exc:
                mark_database_unready()
                raise DatabaseUnavailable("MongoDB could not verify file ownership for deletion.") from exc
    try:
        await detection.delete()
    except PyMongoError as exc:
        mark_database_unready()
        raise DatabaseUnavailable("MongoDB could not delete the detection record.") from exc
    if references and not shared_files:
        cleanup_detection_files(detection)
    return True
