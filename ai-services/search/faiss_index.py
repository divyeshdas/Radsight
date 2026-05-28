import os
import json
import time
import threading
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import numpy as np
import faiss
from core.config import get_ai_settings
import structlog

logger = structlog.get_logger(__name__)
settings = get_ai_settings()

_lock = threading.RLock()

INDEX_META_PATH = Path(settings.faiss_index_path).with_suffix(".meta.json")


class FAISSIndexManager:
    """
    Manages a FAISS index for approximate nearest-neighbor search over
    radiology report embeddings. Uses HNSW for low-latency retrieval
    and falls back to IVFFlat for very large corpora.

    ID mapping: FAISS integer IDs → report_id strings are stored
    in a sidecar JSON file alongside the index.
    """

    def __init__(self):
        self._index: Optional[faiss.Index] = None
        self._id_map: Dict[int, str] = {}
        self._next_id: int = 0
        self._dimension = settings.faiss_dimension
        self._index_path = Path(settings.faiss_index_path)
        self._index_path.parent.mkdir(parents=True, exist_ok=True)

    def _build_hnsw_index(self) -> faiss.Index:
        m = 32
        index = faiss.IndexHNSWFlat(self._dimension, m, faiss.METRIC_INNER_PRODUCT)
        index.hnsw.efConstruction = 200
        index.hnsw.efSearch = 50
        return index

    def _build_ivf_index(self, nlist: int = 100) -> faiss.Index:
        quantizer = faiss.IndexFlatIP(self._dimension)
        index = faiss.IndexIVFFlat(quantizer, self._dimension, nlist, faiss.METRIC_INNER_PRODUCT)
        return index

    def _wrap_with_id_map(self, index: faiss.Index) -> faiss.IndexIDMap:
        return faiss.IndexIDMap(index)

    def initialize(self, corpus_size_hint: int = 10000) -> None:
        with _lock:
            if self._index is not None:
                return

            if self._index_path.exists():
                self.load()
                return

            if corpus_size_hint > 50000:
                base = self._build_ivf_index(nlist=settings.faiss_nlist)
            else:
                base = self._build_hnsw_index()

            self._index = self._wrap_with_id_map(base)
            self._id_map = {}
            self._next_id = 0
            logger.info("FAISS index initialized", type=type(base).__name__, dim=self._dimension)

    def add(self, embedding: np.ndarray, report_id: str) -> int:
        with _lock:
            if self._index is None:
                self.initialize()

            vec = embedding.astype(np.float32).reshape(1, -1)
            faiss.normalize_L2(vec)

            idx = self._next_id
            self._index.add_with_ids(vec, np.array([idx], dtype=np.int64))
            self._id_map[idx] = report_id
            self._next_id += 1
            return idx

    def add_batch(self, embeddings: np.ndarray, report_ids: List[str]) -> List[int]:
        with _lock:
            if self._index is None:
                self.initialize(corpus_size_hint=len(embeddings))

            vecs = embeddings.astype(np.float32)
            faiss.normalize_L2(vecs)

            start_id = self._next_id
            ids = np.arange(start_id, start_id + len(embeddings), dtype=np.int64)

            if hasattr(self._index, "index") and isinstance(self._index.index, faiss.IndexIVFFlat):
                if not self._index.index.is_trained:
                    logger.info("Training IVF index", n_vectors=len(vecs))
                    self._index.index.train(vecs)

            self._index.add_with_ids(vecs, ids)

            for i, rid in enumerate(report_ids):
                self._id_map[start_id + i] = rid

            self._next_id += len(embeddings)
            return ids.tolist()

    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 10,
        nprobe: int = None,
    ) -> List[Dict]:
        with _lock:
            if self._index is None or self._index.ntotal == 0:
                return []

            vec = query_embedding.astype(np.float32).reshape(1, -1)
            faiss.normalize_L2(vec)

            effective_k = min(k, self._index.ntotal)

            if nprobe and hasattr(self._index, "index"):
                inner = self._index.index
                if hasattr(inner, "nprobe"):
                    inner.nprobe = nprobe or settings.faiss_nprobe

            distances, indices = self._index.search(vec, effective_k)

            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx == -1:
                    continue
                report_id = self._id_map.get(int(idx))
                if report_id:
                    results.append({
                        "report_id": report_id,
                        "faiss_id": int(idx),
                        "score": round(float(dist), 4),
                    })

            return results

    def save(self) -> None:
        with _lock:
            if self._index is None:
                return
            faiss.write_index(self._index, str(self._index_path))
            meta = {"id_map": {str(k): v for k, v in self._id_map.items()}, "next_id": self._next_id}
            INDEX_META_PATH.write_text(json.dumps(meta))
            logger.info("FAISS index saved", path=str(self._index_path), vectors=self._index.ntotal)

    def load(self) -> None:
        with _lock:
            if not self._index_path.exists():
                raise FileNotFoundError(f"FAISS index not found: {self._index_path}")

            self._index = faiss.read_index(str(self._index_path))
            if INDEX_META_PATH.exists():
                meta = json.loads(INDEX_META_PATH.read_text())
                self._id_map = {int(k): v for k, v in meta.get("id_map", {}).items()}
                self._next_id = meta.get("next_id", self._index.ntotal)
            logger.info("FAISS index loaded", vectors=self._index.ntotal)

    def rebuild_from_embeddings(self, embeddings: np.ndarray, report_ids: List[str]) -> None:
        with _lock:
            if len(embeddings) > 50000:
                base = self._build_ivf_index(nlist=min(settings.faiss_nlist, len(embeddings) // 10))
            else:
                base = self._build_hnsw_index()

            self._index = self._wrap_with_id_map(base)
            self._id_map = {}
            self._next_id = 0

        self.add_batch(embeddings, report_ids)
        self.save()
        logger.info("FAISS index rebuilt", total=len(embeddings))

    @property
    def total_vectors(self) -> int:
        return self._index.ntotal if self._index else 0

    @property
    def is_ready(self) -> bool:
        return self._index is not None and self._index.ntotal > 0


faiss_manager = FAISSIndexManager()
