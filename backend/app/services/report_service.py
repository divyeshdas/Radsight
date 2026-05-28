from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId
from app.db.mongodb import get_collection, get_database
from app.db.redis_client import cache_set, cache_get, cache_delete
from app.models.report import RadiologyReport, ReportStatus, SeverityLevel, ReportType, ReportSource
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger

logger = get_logger(__name__)


async def create_report(
    patient_id: str,
    raw_text: str,
    report_type: ReportType = ReportType.chest_xray,
    source: ReportSource = ReportSource.upload,
    institution: Optional[str] = None,
    radiologist_id: Optional[str] = None,
    metadata: dict | None = None,
) -> RadiologyReport:
    collection = get_collection("reports")
    now = datetime.now(timezone.utc)

    doc = {
        "patient_id": patient_id,
        "report_type": report_type,
        "source": source,
        "status": ReportStatus.pending,
        "raw_text": raw_text,
        "cleaned_text": None,
        "word_count": len(raw_text.split()),
        "severity": None,
        "risk_score": None,
        "classification_confidence": None,
        "ai_summary": None,
        "findings_count": 0,
        "has_critical_findings": False,
        "flagged_for_review": False,
        "modality": None,
        "body_region": None,
        "institution": institution,
        "radiologist_id": radiologist_id,
        "processing_time_ms": None,
        "ocr_confidence": None,
        "tags": [],
        "metadata": metadata or {},
        "created_at": now,
        "updated_at": now,
    }

    result = await collection.insert_one(doc)
    report = RadiologyReport(**{**doc, "_id": str(result.inserted_id)})
    logger.info("Report created", report_id=str(result.inserted_id), patient_id=patient_id)
    return report


async def get_report(report_id: str) -> RadiologyReport:
    cache_key = f"report:{report_id}"
    cached = await cache_get(cache_key)
    if cached:
        return RadiologyReport(**cached)

    collection = get_collection("reports")
    doc = await collection.find_one({"_id": ObjectId(report_id)})
    if not doc:
        raise NotFoundError("Report", report_id)

    report = RadiologyReport(**{**doc, "_id": str(doc["_id"])})
    await cache_set(cache_key, report.model_dump(mode="json"), ttl=300)
    return report


async def list_reports(
    patient_id: Optional[str] = None,
    severity: Optional[SeverityLevel] = None,
    status: Optional[ReportStatus] = None,
    report_type: Optional[ReportType] = None,
    flagged: Optional[bool] = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[RadiologyReport], int]:
    collection = get_collection("reports")

    query: dict = {}
    if patient_id:
        query["patient_id"] = patient_id
    if severity:
        query["severity"] = severity
    if status:
        query["status"] = status
    if report_type:
        query["report_type"] = report_type
    if flagged is not None:
        query["flagged_for_review"] = flagged

    total = await collection.count_documents(query)
    projection = {"raw_text": 0, "cleaned_text": 0}
    cursor = collection.find(query, projection).sort("created_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)

    reports = [RadiologyReport(**{**d, "_id": str(d["_id"]), "raw_text": "", "cleaned_text": None}) for d in docs]
    return reports, total


async def update_report_after_processing(
    report_id: str,
    severity: SeverityLevel,
    risk_score: float,
    confidence: float,
    summary: str,
    findings_count: int,
    has_critical: bool,
    processing_time_ms: float,
    cleaned_text: str,
) -> None:
    collection = get_collection("reports")
    await collection.update_one(
        {"_id": ObjectId(report_id)},
        {
            "$set": {
                "status": ReportStatus.completed,
                "severity": severity,
                "risk_score": risk_score,
                "classification_confidence": confidence,
                "ai_summary": summary,
                "findings_count": findings_count,
                "has_critical_findings": has_critical,
                "flagged_for_review": severity in (SeverityLevel.high, SeverityLevel.critical),
                "cleaned_text": cleaned_text,
                "processing_time_ms": processing_time_ms,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
    await cache_delete(f"report:{report_id}")


async def delete_report(report_id: str) -> None:
    collection = get_collection("reports")
    result = await collection.delete_one({"_id": ObjectId(report_id)})
    if result.deleted_count == 0:
        raise NotFoundError("Report", report_id)

    db = get_database()
    await db["findings"].delete_many({"report_id": report_id})
    await db["severity_scores"].delete_one({"report_id": report_id})
    await db["nlp_entities"].delete_many({"report_id": report_id})
    await db["embeddings"].delete_one({"report_id": report_id})
    await cache_delete(f"report:{report_id}")
    logger.info("Report deleted", report_id=report_id)


async def get_report_stats() -> dict:
    cache_key = "report:stats:summary"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    db = get_database()
    pipeline = [
        {
            "$group": {
                "_id": None,
                "total": {"$sum": 1},
                "completed": {"$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}},
                "critical": {"$sum": {"$cond": [{"$eq": ["$severity", "critical"]}, 1, 0]}},
                "flagged": {"$sum": {"$cond": ["$flagged_for_review", 1, 0]}},
                "avg_risk": {"$avg": "$risk_score"},
                "avg_processing_ms": {"$avg": "$processing_time_ms"},
            }
        }
    ]
    result = await db["reports"].aggregate(pipeline).to_list(1)
    stats = result[0] if result else {}
    stats.pop("_id", None)

    await cache_set(cache_key, stats, ttl=60)
    return stats
