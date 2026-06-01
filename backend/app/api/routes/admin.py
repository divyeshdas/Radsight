from fastapi import APIRouter
from app.api.dependencies.auth import AdminUser
from app.db.mongodb import get_database
from app.core.logging import get_logger

router = APIRouter(prefix="/admin", tags=["admin"])
logger = get_logger(__name__)


@router.post("/backfill-severity")
async def backfill_severity(current_user: AdminUser):
    from app.services.scan_processor import analyze_text
    import time

    db = get_database()
    collection = db["reports"]

    total = await collection.count_documents({"severity": None})
    if total == 0:
        return {"message": "Nothing to backfill — all reports already have severity set.", "updated": 0}

    updated = 0
    failed = 0

    async for doc in collection.find({"severity": None}, {"_id": 1, "raw_text": 1, "patient_id": 1}):
        try:
            raw = doc.get("raw_text") or ""
            patient = doc.get("patient_id", "")
            start = time.monotonic()
            result = analyze_text(raw, patient)
            ms = round((time.monotonic() - start) * 1000 + 50, 1)

            await collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {
                    "severity": result["severity"],
                    "risk_score": result["risk_score"],
                    "classification_confidence": result["classification_confidence"],
                    "findings_count": result["findings_count"],
                    "has_critical_findings": result["has_critical_findings"],
                    "flagged_for_review": result["flagged_for_review"],
                    "tags": result["tags"],
                    "ai_summary": result["ai_summary"],
                    "processing_time_ms": ms,
                    "status": "completed",
                }}
            )
            updated += 1
        except Exception as e:
            logger.warning("backfill row failed", doc_id=str(doc["_id"]), error=str(e))
            failed += 1

    logger.info("Severity backfill complete", updated=updated, failed=failed)
    return {
        "message": f"Backfill complete.",
        "total_found": total,
        "updated": updated,
        "failed": failed,
    }
