import hashlib
import time
from typing import List, Optional, Dict
import numpy as np
import redis.asyncio as aioredis
from core.model_registry import registry
from core.config import get_ai_settings
import structlog

logger = structlog.get_logger(__name__)
settings = get_ai_settings()

_redis_client: Optional[aioredis.Redis] = None
_tiered_cache = None


def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password or None,
            db=settings.redis_db,
            decode_responses=False,
        )
    return _redis_client


def _get_cache():
    global _tiered_cache
    if _tiered_cache is None:
        from core.tiered_cache import get_tiered_cache
        _tiered_cache = get_tiered_cache(get_redis())
    return _tiered_cache


def _cache_key(text: str) -> str:
    digest = hashlib.sha256(text.encode()).hexdigest()[:32]
    return f"emb:{digest}"


def _encode_texts(texts: List[str]) -> np.ndarray:
    """Encode with ORT if available, fall back to sentence_transformers."""
    ort = registry.ort_sentencebert
    if ort is not None:
        try:
            return ort.encode_batch(texts)
        except Exception as exc:
            logger.warning("ORT encoding failed, using sentence_transformers", error=str(exc))

    model = registry.load_sentence_model()
    embs = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
    return np.array(embs, dtype=np.float32)


async def generate_embedding(text: str, use_cache: bool = True) -> Dict:
    t0 = time.perf_counter()
    key = _cache_key(text)

    if use_cache:
        cached = await _get_cache().get(key)
        if cached is not None:
            arr = np.frombuffer(cached, dtype=np.float32)
            return {
                "embedding": arr.tolist(),
                "dimension": len(arr),
                "cache_hit": True,
                "inference_ms": round((time.perf_counter() - t0) * 1000, 2),
            }

    truncated = " ".join(text.split()[:400])
    embedding = _encode_texts([truncated])[0]

    if use_cache:
        await _get_cache().set(key, embedding.tobytes(), ttl=settings.redis_embedding_ttl)

    return {
        "embedding": embedding.tolist(),
        "dimension": len(embedding),
        "cache_hit": False,
        "inference_ms": round((time.perf_counter() - t0) * 1000, 2),
    }


async def generate_batch_embeddings(
    texts: List[str],
    use_cache: bool = True,
    batch_size: int = 16,
) -> List[Dict]:
    results: List[Optional[Dict]] = [None] * len(texts)
    uncached_indices: List[int] = []
    uncached_texts: List[str] = []

    cache = _get_cache()

    for i, text in enumerate(texts):
        if use_cache:
            key = _cache_key(text)
            cached = await cache.get(key)
            if cached is not None:
                arr = np.frombuffer(cached, dtype=np.float32)
                results[i] = {
                    "embedding": arr.tolist(),
                    "dimension": len(arr),
                    "cache_hit": True,
                    "inference_ms": 0.0,
                }
                continue

        uncached_indices.append(i)
        uncached_texts.append(" ".join(text.split()[:400]))

    if uncached_texts:
        t0 = time.perf_counter()
        all_embeddings: List[np.ndarray] = []

        for start in range(0, len(uncached_texts), batch_size):
            batch = uncached_texts[start:start + batch_size]
            batch_embs = _encode_texts(batch)
            all_embeddings.extend(batch_embs)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        per_ms = elapsed_ms / max(len(uncached_texts), 1)

        for j, idx in enumerate(uncached_indices):
            emb = all_embeddings[j].astype(np.float32)
            if use_cache:
                await cache.set(
                    _cache_key(texts[idx]),
                    emb.tobytes(),
                    ttl=settings.redis_embedding_ttl,
                )
            results[idx] = {
                "embedding": emb.tolist(),
                "dimension": len(emb),
                "cache_hit": False,
                "inference_ms": round(per_ms, 2),
            }

    return results  # type: ignore[return-value]
