from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import motor.motor_asyncio
import structlog

logger = structlog.get_logger(__name__)


async def get_kpi_summary(db: motor.motor_asyncio.AsyncIOMotorDatabase) -> Dict:
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)

    pipeline = [
        {
            "$facet": {
                "total": [{"$count": "n"}],
                "today": [
                    {"$match": {"created_at": {"$gte": today}}},
                    {"$count": "n"},
                ],
                "critical": [
                    {"$match": {"severity": "critical"}},
                    {"$count": "n"},
                ],
                "flagged": [
                    {"$match": {"flagged_for_review": True, "status": "completed"}},
                    {"$count": "n"},
                ],
                "avg_risk": [
                    {"$match": {"risk_score": {"$ne": None}}},
                    {"$group": {"_id": None, "avg": {"$avg": "$risk_score"}}},
                ],
                "avg_processing": [
                    {"$match": {"processing_time_ms": {"$ne": None}}},
                    {"$group": {"_id": None, "avg": {"$avg": "$processing_time_ms"}}},
                ],
                "week_completed": [
                    {"$match": {"status": "completed", "created_at": {"$gte": week_ago}}},
                    {"$count": "n"},
                ],
            }
        }
    ]

    result = await db["reports"].aggregate(pipeline).to_list(1)
    data = result[0] if result else {}

    return {
        "total_reports": (data.get("total") or [{"n": 0}])[0].get("n", 0),
        "reports_today": (data.get("today") or [{"n": 0}])[0].get("n", 0),
        "critical_cases": (data.get("critical") or [{"n": 0}])[0].get("n", 0),
        "flagged_for_review": (data.get("flagged") or [{"n": 0}])[0].get("n", 0),
        "avg_risk_score": round((data.get("avg_risk") or [{"avg": 0}])[0].get("avg", 0) or 0, 4),
        "avg_processing_ms": round((data.get("avg_processing") or [{"avg": 0}])[0].get("avg", 0) or 0, 1),
        "reports_this_week": (data.get("week_completed") or [{"n": 0}])[0].get("n", 0),
    }


async def get_severity_distribution(
    db: motor.motor_asyncio.AsyncIOMotorDatabase,
    days: int = 30,
) -> List[Dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    pipeline = [
        {"$match": {"created_at": {"$gte": since}, "severity": {"$ne": None}}},
        {"$group": {"_id": "$severity", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    result = await db["reports"].aggregate(pipeline).to_list(20)
    return [{"severity": r["_id"], "count": r["count"]} for r in result]


async def get_disease_prevalence(
    db: motor.motor_asyncio.AsyncIOMotorDatabase,
    days: int = 30,
    limit: int = 10,
) -> List[Dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    pipeline = [
        {"$match": {"created_at": {"$gte": since}}},
        {"$unwind": "$tags"},
        {
            "$match": {
                "tags": {
                    "$nin": [
                        "normal", "mild", "moderate", "severe", "critical",
                        "cardiovascular-pulmonary", "pleural", "infectious",
                        "neoplastic", "cardiac", "pulmonary", "traumatic",
                    ]
                }
            }
        },
        {"$group": {"_id": "$tags", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit},
    ]
    result = await db["reports"].aggregate(pipeline).to_list(limit)
    return [{"disease": r["_id"], "count": r["count"]} for r in result]


async def get_daily_report_counts(
    db: motor.motor_asyncio.AsyncIOMotorDatabase,
    days: int = 90,
) -> List[Dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    pipeline = [
        {"$match": {"created_at": {"$gte": since}}},
        {
            "$group": {
                "_id": {
                    "$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}
                },
                "total_reports": {"$sum": 1},
                "processed": {"$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}},
                "critical_count": {"$sum": {"$cond": [{"$eq": ["$severity", "critical"]}, 1, 0]}},
                "flagged_count": {"$sum": {"$cond": ["$flagged_for_review", 1, 0]}},
                "avg_risk_score": {"$avg": "$risk_score"},
                "severity_distribution": {
                    "$push": "$severity"
                },
            }
        },
        {"$sort": {"_id": 1}},
    ]
    result = await db["reports"].aggregate(pipeline).to_list(days + 5)

    rows = []
    for r in result:
        sev_list = [s for s in r.get("severity_distribution", []) if s]
        sev_counts = {}
        for s in sev_list:
            sev_counts[s] = sev_counts.get(s, 0) + 1

        rows.append({
            "date": r["_id"],
            "total_reports": r["total_reports"],
            "processed_reports": r.get("processed", 0),
            "critical_count": r.get("critical_count", 0),
            "flagged_count": r.get("flagged_count", 0),
            "avg_risk_score": round(float(r.get("avg_risk_score") or 0), 4),
            "severity_distribution": sev_counts,
            "disease_counts": {},
        })

    return rows


async def get_processing_metrics(
    db: motor.motor_asyncio.AsyncIOMotorDatabase,
    hours: int = 24,
) -> Dict:
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    pipeline = [
        {"$match": {"created_at": {"$gte": since}}},
        {
            "$group": {
                "_id": None,
                "total": {"$sum": 1},
                "completed": {"$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}},
                "failed": {"$sum": {"$cond": [{"$eq": ["$status", "failed"]}, 1, 0]}},
                "pending": {"$sum": {"$cond": [{"$eq": ["$status", "pending"]}, 1, 0]}},
                "avg_ms": {"$avg": "$processing_time_ms"},
                "p95_ms": {"$push": "$processing_time_ms"},
            }
        }
    ]
    result = await db["reports"].aggregate(pipeline).to_list(1)
    if not result:
        return {}

    data = result[0]
    ms_values = [v for v in data.get("p95_ms", []) if v is not None]

    import numpy as np
    p95 = round(float(np.percentile(ms_values, 95)), 1) if ms_values else 0

    elapsed_hours = max(hours, 1)
    throughput = round(data.get("completed", 0) / (elapsed_hours * 60), 2)

    return {
        "window_hours": hours,
        "total": data.get("total", 0),
        "completed": data.get("completed", 0),
        "failed": data.get("failed", 0),
        "pending": data.get("pending", 0),
        "avg_processing_ms": round(float(data.get("avg_ms") or 0), 1),
        "p95_processing_ms": p95,
        "throughput_per_minute": throughput,
        "success_rate_pct": round(data.get("completed", 0) / max(data.get("total", 1), 1) * 100, 1),
    }


async def get_confidence_distribution(
    db: motor.motor_asyncio.AsyncIOMotorDatabase,
    days: int = 30,
    buckets: int = 10,
) -> List[Dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    pipeline = [
        {"$match": {"created_at": {"$gte": since}, "classification_confidence": {"$ne": None}}},
        {
            "$bucket": {
                "groupBy": "$classification_confidence",
                "boundaries": [i / buckets for i in range(buckets + 1)],
                "default": "other",
                "output": {"count": {"$sum": 1}},
            }
        },
    ]
    result = await db["reports"].aggregate(pipeline).to_list(buckets + 2)
    return [
        {"range": f"{r['_id']:.1f}–{r['_id'] + 0.1:.1f}", "count": r["count"]}
        for r in result
        if isinstance(r.get("_id"), (int, float))
    ]
