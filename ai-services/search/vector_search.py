import hashlib
import json
import time
from typing import List, Dict, Optional
import numpy as np
import redis.asyncio as aioredis
import motor.motor_asyncio

from search.faiss_index import faiss_manager
from embeddings.sentence_bert import generate_embedding
from core.config import get_ai_settings
import structlog

logger = structlog.get_logger(__name__)
settings = get_ai_settings()

_redis: Optional[aioredis.Redis] = None
_mongo: Optional[motor.motor_asyncio.AsyncIOMotorDatabase] = None

CACHE_HITS = [0]
CACHE_MISSES = [0]


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password or None,
            db=settings.redis_db,
            decode_responses=False,
        )
    return _redis


def get_db() -> motor.motor_asyncio.AsyncIOMotorDatabase:
    global _mongo
    if _mongo is None:
        client = motor.motor_asyncio.AsyncIOMotorClient(settings.mongodb_uri)
        _mongo = client[settings.mongodb_db_name]
    return _mongo


def _query_cache_key(query: str) -> str:
    return f"qemb:{hashlib.sha256(query.encode()).hexdigest()[:32]}"


async def _get_query_embedding_cached(query: str) -> np.ndarray:
    key = _query_cache_key(query)
    r = get_redis()

    try:
        cached = await r.get(key)
        if cached:
            CACHE_HITS[0] += 1
            return np.frombuffer(cached, dtype=np.float32)
    except Exception:
        pass

    CACHE_MISSES[0] += 1
    result = await generate_embedding(query, use_cache=True)
    emb = np.array(result["embedding"], dtype=np.float32)

    try:
        await r.set(key, emb.tobytes(), ex=settings.redis_embedding_ttl)
    except Exception:
        pass

    return emb


async def _enrich_results(raw_results: List[Dict]) -> List[Dict]:
    if not raw_results:
        return []

    db = get_db()
    report_ids = [r["report_id"] for r in raw_results]
    score_map = {r["report_id"]: r["score"] for r in raw_results}

    from bson import ObjectId
    valid_ids = []
    for rid in report_ids:
        try:
            valid_ids.append(ObjectId(rid))
        except Exception:
            pass

    projection = {
        "patient_id": 1,
        "report_type": 1,
        "severity": 1,
        "risk_score": 1,
        "ai_summary": 1,
        "findings_count": 1,
        "has_critical_findings": 1,
        "created_at": 1,
        "institution": 1,
    }

    docs = await db["reports"].find(
        {"_id": {"$in": valid_ids}},
        projection,
    ).to_list(length=len(valid_ids))

    doc_map = {str(d["_id"]): d for d in docs}

    enriched = []
    for rid in report_ids:
        doc = doc_map.get(rid)
        if not doc:
            continue
        enriched.append({
            "report_id": rid,
            "patient_id": doc.get("patient_id"),
            "report_type": doc.get("report_type"),
            "severity": doc.get("severity"),
            "risk_score": doc.get("risk_score"),
            "summary": doc.get("ai_summary", "")[:300],
            "findings_count": doc.get("findings_count", 0),
            "has_critical_findings": doc.get("has_critical_findings", False),
            "created_at": doc.get("created_at", "").isoformat() if hasattr(doc.get("created_at"), "isoformat") else str(doc.get("created_at", "")),
            "institution": doc.get("institution"),
            "similarity_score": score_map.get(rid, 0.0),
        })

    enriched.sort(key=lambda x: -x["similarity_score"])
    return enriched


async def semantic_search(
    query: str,
    k: int = 10,
    severity_filter: Optional[str] = None,
    min_score: float = 0.30,
) -> Dict:
    t0 = time.perf_counter()

    if not faiss_manager.is_ready:
        return {
            "results": [],
            "total": 0,
            "query": query,
            "inference_ms": 0.0,
            "index_ready": False,
            "message": "Index not yet built. Ingest reports first.",
        }

    query_embedding = await _get_query_embedding_cached(query)

    raw = faiss_manager.search(query_embedding, k=k * 2)
    filtered = [r for r in raw if r["score"] >= min_score]

    if severity_filter:
        enriched_all = await _enrich_results(filtered)
        enriched = [r for r in enriched_all if r.get("severity") == severity_filter][:k]
    else:
        enriched = await _enrich_results(filtered[:k])

    elapsed_ms = (time.perf_counter() - t0) * 1000

    total = CACHE_HITS[0] + CACHE_MISSES[0]
    hit_rate = round(CACHE_HITS[0] / max(total, 1) * 100, 1)

    return {
        "results": enriched,
        "total": len(enriched),
        "query": query,
        "inference_ms": round(elapsed_ms, 2),
        "index_ready": True,
        "index_size": faiss_manager.total_vectors,
        "cache_hit_rate_pct": hit_rate,
    }


async def index_report_embedding(report_id: str, embedding: List[float]) -> int:
    vec = np.array(embedding, dtype=np.float32)
    faiss_idx = faiss_manager.add(vec, report_id)
    return faiss_idx


async def build_index_from_mongodb() -> Dict:
    db = get_db()
    t0 = time.perf_counter()

    logger.info("Building FAISS index from MongoDB embeddings")

    embedding_docs = await db["embeddings"].find({}).to_list(length=200000)
    if not embedding_docs:
        return {"status": "error", "message": "No embeddings found in database"}

    report_ids = [d["report_id"] for d in embedding_docs]
    pipeline_results = await db["reports"].find(
        {"_id": {"$in": [__import__("bson").ObjectId(rid) for rid in report_ids]}},
        {"ai_summary": 1, "raw_text": 1},
    ).to_list(length=len(report_ids))

    texts_map = {str(d["_id"]): d.get("ai_summary") or d.get("raw_text", "")[:500] for d in pipeline_results}
    texts = [texts_map.get(rid, "") for rid in report_ids]

    valid_pairs = [(rid, t) for rid, t in zip(report_ids, texts) if t.strip()]
    if not valid_pairs:
        return {"status": "error", "message": "No report text found"}

    valid_report_ids, valid_texts = zip(*valid_pairs)

    from embeddings.sentence_bert import generate_batch_embeddings
    emb_results = await generate_batch_embeddings(list(valid_texts), use_cache=True, batch_size=32)
    embeddings = np.array([r["embedding"] for r in emb_results], dtype=np.float32)

    faiss_manager.rebuild_from_embeddings(embeddings, list(valid_report_ids))

    elapsed = round((time.perf_counter() - t0), 2)
    return {
        "status": "success",
        "indexed": faiss_manager.total_vectors,
        "elapsed_seconds": elapsed,
    }


def get_cache_stats() -> Dict:
    total = CACHE_HITS[0] + CACHE_MISSES[0]
    return {
        "cache_hits": CACHE_HITS[0],
        "cache_misses": CACHE_MISSES[0],
        "hit_rate_pct": round(CACHE_HITS[0] / max(total, 1) * 100, 1),
        "index_size": faiss_manager.total_vectors,
    }
