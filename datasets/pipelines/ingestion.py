import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Optional, AsyncIterator
import motor.motor_asyncio
from datasets.pipelines.preprocessing import preprocess_report


BATCH_SIZE = 500
MAX_CONCURRENT_BATCHES = 4


async def _insert_batch(
    collection: motor.motor_asyncio.AsyncIOMotorCollection,
    batch: List[Dict],
    processed: List[int],
) -> int:
    if not batch:
        return 0
    try:
        result = await collection.insert_many(batch, ordered=False)
        count = len(result.inserted_ids)
        processed[0] += count
        return count
    except Exception as e:
        failed = [b for b in batch if "_id" not in b]
        if failed:
            try:
                result = await collection.insert_many(failed, ordered=False)
                count = len(result.inserted_ids)
                processed[0] += count
                return count
            except Exception:
                pass
        return 0


async def _batched_stream(items: List[Dict], size: int) -> AsyncIterator[List[Dict]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


async def ingest_reports(
    reports: List[Dict],
    mongodb_uri: str,
    db_name: str = "radsight",
    preprocess: bool = True,
    progress_callback: Optional[callable] = None,
    batch_size: int = BATCH_SIZE,
) -> Dict:
    client = motor.motor_asyncio.AsyncIOMotorClient(
        mongodb_uri,
        maxPoolSize=10,
        serverSelectionTimeoutMS=10000,
    )
    db = client[db_name]
    reports_col = db["reports"]
    analytics_col = db["analytics"]

    total = len(reports)
    processed = [0]
    failed = [0]
    start_time = datetime.now(timezone.utc)

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_BATCHES)

    async def process_and_insert(batch: List[Dict]) -> int:
        async with semaphore:
            enriched = []
            for doc in batch:
                try:
                    if preprocess and doc.get("raw_text"):
                        result = preprocess_report(doc["raw_text"])
                        doc["cleaned_text"] = result["cleaned_text"]
                        doc["word_count"] = result["word_count"]
                        doc["metadata"]["negation_count"] = result["negation_count"]
                        doc["metadata"]["has_impression"] = result["has_impression_section"]
                    enriched.append(doc)
                except Exception:
                    failed[0] += 1

            return await _insert_batch(reports_col, enriched, processed)

    tasks = []
    async for batch in _batched_stream(reports, batch_size):
        tasks.append(asyncio.create_task(process_and_insert(batch)))

        if len(tasks) >= MAX_CONCURRENT_BATCHES * 2:
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            tasks = list(pending)
            if progress_callback:
                progress_callback(processed[0], total)

    if tasks:
        await asyncio.gather(*tasks)

    if progress_callback:
        progress_callback(processed[0], total)

    await _update_daily_analytics(analytics_col, reports)

    end_time = datetime.now(timezone.utc)
    elapsed = (end_time - start_time).total_seconds()

    client.close()

    return {
        "total_submitted": total,
        "inserted": processed[0],
        "failed": failed[0],
        "elapsed_seconds": round(elapsed, 2),
        "throughput_per_second": round(processed[0] / max(elapsed, 0.001), 2),
    }


async def _update_daily_analytics(
    collection: motor.motor_asyncio.AsyncIOMotorCollection,
    reports: List[Dict],
) -> None:
    daily: Dict[str, Dict] = {}

    for r in reports:
        created = r.get("created_at")
        if isinstance(created, datetime):
            date_str = created.strftime("%Y-%m-%d")
        else:
            continue

        if date_str not in daily:
            daily[date_str] = {
                "date": date_str,
                "total_reports": 0,
                "processed_reports": 0,
                "severity_distribution": {},
                "disease_counts": {},
            }

        daily[date_str]["total_reports"] += 1
        if r.get("status") == "completed":
            daily[date_str]["processed_reports"] += 1

        severity = r.get("severity", "unknown")
        daily[date_str]["severity_distribution"][severity] = (
            daily[date_str]["severity_distribution"].get(severity, 0) + 1
        )

        disease = r.get("metadata", {}).get("disease", "unknown")
        daily[date_str]["disease_counts"][disease] = (
            daily[date_str]["disease_counts"].get(disease, 0) + 1
        )

    if not daily:
        return

    ops = [
        motor.motor_asyncio.AsyncIOMotorCollection.update_one
        for _ in daily
    ]

    update_tasks = [
        collection.update_one(
            {"date": date_str},
            {"$inc": {
                "total_reports": data["total_reports"],
                "processed_reports": data["processed_reports"],
            }, "$set": {
                "date": date_str,
                "updated_at": datetime.now(timezone.utc),
            }},
            upsert=True,
        )
        for date_str, data in daily.items()
    ]

    await asyncio.gather(*update_tasks)
