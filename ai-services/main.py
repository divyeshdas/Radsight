import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
import motor.motor_asyncio
from datetime import datetime, timezone

from core.config import get_ai_settings
from core.model_registry import registry
from nlp.pipeline import run_full_pipeline, run_batch_pipeline
from ocr.paddle_ocr import extract_text
from search.vector_search import semantic_search, index_report_embedding, build_index_from_mongodb, get_cache_stats
from search.faiss_index import faiss_manager
import structlog

logger = structlog.get_logger(__name__)
settings = get_ai_settings()

_db_client = None


def get_db():
    global _db_client
    if _db_client is None:
        _db_client = motor.motor_asyncio.AsyncIOMotorClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=5000,
        )
    return _db_client[settings.mongodb_db_name]


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AI Services starting — loading models")
    try:
        registry.load_spacy()
        logger.info("scispaCy loaded")
    except Exception as e:
        logger.warning("scispaCy load failed", error=str(e))

    try:
        registry.load_sentence_model()
        logger.info("Sentence-BERT loaded")
    except Exception as e:
        logger.warning("Sentence-BERT load failed", error=str(e))

    try:
        registry.load_onnx_sessions()
        cb_ok = registry.ort_clinicalbert is not None
        sb_ok = registry.ort_sentencebert is not None
        logger.info("ONNX sessions loaded", clinicalbert=cb_ok, sentencebert=sb_ok)
    except Exception as e:
        logger.warning("ONNX session load failed", error=str(e))

    try:
        faiss_manager.initialize()
        logger.info("FAISS index initialized", vectors=faiss_manager.total_vectors)
    except Exception as e:
        logger.warning("FAISS init failed", error=str(e))

    logger.info("AI Services ready — heavy models load on first request")
    yield
    try:
        if faiss_manager.total_vectors > 0:
            faiss_manager.save()
    except Exception:
        pass
    logger.info("AI Services shutdown")


app = FastAPI(
    title="RadSight AI Services",
    version="1.0.0",
    lifespan=lifespan,
)


class NLPRequest(BaseModel):
    text: str
    use_biobert: bool = True
    use_embeddings: bool = True


class BatchNLPRequest(BaseModel):
    reports: List[dict]
    use_biobert: bool = True


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "ai-services"}


@app.post("/nlp/analyze")
async def analyze_text(request: NLPRequest):
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    result = await run_full_pipeline(
        report_id="",
        text=request.text,
        use_biobert=request.use_biobert,
        use_embeddings=request.use_embeddings,
    )
    return result


@app.post("/nlp/process/{report_id}")
async def process_report(report_id: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(_process_and_update, report_id)
    return {"report_id": report_id, "status": "processing"}


@app.post("/nlp/batch")
async def batch_analyze(request: BatchNLPRequest):
    results = await run_batch_pipeline(
        reports=request.reports,
        use_biobert=request.use_biobert,
    )
    return {"results": results, "count": len(results)}


@app.post("/ocr/extract")
async def ocr_extract(file: UploadFile = File(...)):
    content = await file.read()
    ext = (file.filename or "").rsplit(".", 1)[-1] if file.filename else "txt"
    result = extract_text(content, ext)
    if not result["success"]:
        raise HTTPException(status_code=422, detail="Could not extract text from file")
    return result


@app.post("/ocr/process/{report_id}")
async def ocr_process_report(report_id: str, file: UploadFile = File(...)):
    content = await file.read()
    ext = (file.filename or "").rsplit(".", 1)[-1] if file.filename else "txt"
    ocr_result = extract_text(content, ext)

    if ocr_result["success"]:
        nlp_result = await run_full_pipeline(
            report_id=report_id,
            text=ocr_result["text"],
            use_biobert=True,
            use_embeddings=True,
        )
        await _update_report_in_db(report_id, nlp_result, ocr_result["confidence"])

    return {"report_id": report_id, "ocr": ocr_result}


async def _process_and_update(report_id: str) -> None:
    db = get_db()
    from bson import ObjectId

    try:
        doc = await db["reports"].find_one({"_id": ObjectId(report_id)})
        if not doc:
            logger.warning("Report not found for NLP processing", report_id=report_id)
            return

        text = doc.get("raw_text") or doc.get("cleaned_text") or ""
        if not text.strip():
            return

        result = await run_full_pipeline(
            report_id=report_id,
            text=text,
            use_biobert=True,
            use_embeddings=True,
        )
        await _update_report_in_db(report_id, result, None)

    except Exception as e:
        logger.error("NLP processing failed", report_id=report_id, error=str(e))
        await db["reports"].update_one(
            {"_id": ObjectId(report_id)},
            {"$set": {"status": "failed", "updated_at": datetime.now(timezone.utc)}},
        )


async def _update_report_in_db(report_id: str, result: dict, ocr_confidence: Optional[float]) -> None:
    db = get_db()
    from bson import ObjectId
    now = datetime.now(timezone.utc)

    await db["reports"].update_one(
        {"_id": ObjectId(report_id)},
        {"$set": {
            "status": "completed",
            "severity": result.get("severity"),
            "risk_score": result.get("risk_score"),
            "classification_confidence": result.get("classification_confidence"),
            "ai_summary": result.get("ai_summary"),
            "findings_count": result.get("findings_count", 0),
            "has_critical_findings": result.get("has_critical_findings", False),
            "flagged_for_review": result.get("severity") in ("severe", "critical"),
            "processing_time_ms": result.get("total_inference_ms"),
            "ocr_confidence": ocr_confidence,
            "updated_at": now,
        }},
    )

    if result.get("entities"):
        entity_docs = [
            {**e, "report_id": report_id, "created_at": now}
            for e in result["entities"]
        ]
        if entity_docs:
            await db["nlp_entities"].insert_many(entity_docs, ordered=False)

    if result.get("risk_score") is not None:
        await db["severity_scores"].update_one(
            {"report_id": report_id},
            {"$set": {
                "report_id": report_id,
                "overall_score": result["risk_score"],
                "risk_level": result["risk_level"],
                "urgency_score": result.get("urgency_score", 0),
                "complexity_score": result.get("risk_explainability", {}).get("disease_count", 0) * 0.15,
                "critical_findings": result.get("critical_findings", []),
                "recommendations": result.get("recommendations", []),
                "explainability": result.get("risk_explainability", {}),
                "created_at": now,
            }},
            upsert=True,
        )

    if result.get("embedding"):
        import numpy as np
        await db["embeddings"].update_one(
            {"report_id": report_id},
            {"$set": {
                "report_id": report_id,
                "model": "sentence-bert",
                "dimension": len(result["embedding"]),
                "summary_used": result.get("ai_summary", "")[:200],
                "created_at": now,
            }},
            upsert=True,
        )

        faiss_idx = await index_report_embedding(report_id, result["embedding"])
        await db["embeddings"].update_one(
            {"report_id": report_id},
            {"$set": {"faiss_index_id": faiss_idx}},
        )


# ─── Search routes ────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str
    k: int = 10
    severity_filter: Optional[str] = None
    min_score: float = 0.30


@app.post("/search/semantic")
async def search_semantic(request: SearchRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    return await semantic_search(
        query=request.query,
        k=request.k,
        severity_filter=request.severity_filter,
        min_score=request.min_score,
    )


@app.post("/search/index/rebuild")
async def rebuild_index():
    result = await build_index_from_mongodb()
    return result


@app.get("/search/stats")
async def search_stats():
    return get_cache_stats()
