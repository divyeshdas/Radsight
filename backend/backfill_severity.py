"""
Run once to backfill severity/risk/confidence for reports that have severity=null.
Usage: python backfill_severity.py
Reads MONGODB_URL from env (same var the app uses).
"""
import asyncio
import os
import sys
import time
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, os.path.dirname(__file__))
from app.services.scan_processor import analyze_text


async def run():
    mongo_url = os.environ.get("MONGODB_URL") or os.environ.get("MONGO_URL")
    if not mongo_url:
        print("ERROR: set MONGODB_URL env var")
        sys.exit(1)

    client = AsyncIOMotorClient(mongo_url)
    db = client.get_default_database()
    collection = db["reports"]

    total = await collection.count_documents({"severity": None})
    print(f"Reports with null severity: {total}")
    if total == 0:
        print("Nothing to backfill.")
        return

    updated = 0
    async for doc in collection.find({"severity": None}, {"_id": 1, "raw_text": 1, "patient_id": 1}):
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
        if updated % 100 == 0:
            print(f"  {updated}/{total} done...")

    print(f"Backfill complete. Updated {updated} reports.")
    client.close()


if __name__ == "__main__":
    asyncio.run(run())
