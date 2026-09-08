from typing import Any

from beanie.operators import RegEx
from bson import ObjectId

from backend.database.mongodb import is_database_ready
from backend.models.detection import Detection


class DatabaseUnavailable(RuntimeError):
    pass





async def create_detection(payload: dict[str, Any]) -> Detection:
    _require_database()
    detection = Detection(**payload)
    await detection.insert()
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
    total = await query.count()
    items = (
        await query.sort("-uploaded_at")
        .skip((page - 1) * limit)
        .limit(limit)
        .to_list()
    )

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
    return await Detection.get(ObjectId(detection_id))


