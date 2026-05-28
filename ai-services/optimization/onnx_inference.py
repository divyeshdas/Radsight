"""
ONNX Runtime inference wrappers for ClinicalBERT and Sentence-BERT.
Both sessions are loaded once and reused. INT8 dynamic quantization
(applied by onnx_exporter.py) gives ~2-3x CPU throughput over FP32 PyTorch.
"""

from pathlib import Path
from typing import List, Optional, TYPE_CHECKING
import numpy as np
import structlog

if TYPE_CHECKING:
    import onnxruntime as ort
    from transformers import PreTrainedTokenizerFast

logger = structlog.get_logger(__name__)

LABELS = ["normal", "abnormal", "critical"]


def _make_session(model_path: str) -> "ort.InferenceSession":
    import onnxruntime as ort

    opts = ort.SessionOptions()
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    opts.intra_op_num_threads = 4
    opts.inter_op_num_threads = 1

    return ort.InferenceSession(
        model_path,
        sess_options=opts,
        providers=["CPUExecutionProvider"],
    )


class ClinicalBERTORT:
    def __init__(self, model_path: str, tokenizer_name: str):
        self._session = _make_session(model_path)
        from transformers import AutoTokenizer
        self._tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
        logger.info("ClinicalBERT ORT session loaded", path=model_path)

    def predict_batch(self, texts: List[str]) -> np.ndarray:
        """
        Run batched classification. Returns probability matrix [batch, 3].
        Softmax is computed in numpy to avoid any PyTorch dependency here.
        """
        enc = self._tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="np",
        )
        feed = {
            k: enc[k].astype(np.int64)
            for k in ("input_ids", "attention_mask", "token_type_ids")
            if k in enc
        }
        logits: np.ndarray = self._session.run(None, feed)[0]

        shifted = logits - logits.max(axis=-1, keepdims=True)
        exp = np.exp(shifted)
        return (exp / exp.sum(axis=-1, keepdims=True)).astype(np.float32)

    def predict_one(self, text: str) -> tuple:
        probs = self.predict_batch([text])[0]
        scores = {label: round(float(p), 4) for label, p in zip(LABELS, probs)}
        pred = max(scores, key=scores.__getitem__)
        return pred, scores[pred], scores


class SentenceBERTORT:
    def __init__(self, model_path: str, tokenizer_name: str):
        self._session = _make_session(model_path)
        from transformers import AutoTokenizer
        self._tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
        logger.info("Sentence-BERT ORT session loaded", path=model_path)

    def encode_batch(self, texts: List[str]) -> np.ndarray:
        """
        Encode texts to normalized embeddings [batch, dim].
        Mean pooling over attended tokens replicates sentence_transformers behavior.
        """
        enc = self._tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="np",
        )
        feed = {
            k: enc[k].astype(np.int64)
            for k in ("input_ids", "attention_mask", "token_type_ids")
            if k in enc
        }

        last_hidden: np.ndarray = self._session.run(None, feed)[0]

        mask = enc["attention_mask"][..., np.newaxis].astype(np.float32)
        pooled = (last_hidden * mask).sum(axis=1) / mask.sum(axis=1).clip(min=1e-9)

        norms = np.linalg.norm(pooled, axis=-1, keepdims=True).clip(min=1e-9)
        return (pooled / norms).astype(np.float32)

    def encode_one(self, text: str) -> np.ndarray:
        return self.encode_batch([text])[0]


def load_clinicalbert_ort(onnx_dir: str, model_name: str) -> Optional["ClinicalBERTORT"]:
    int8_path = Path(onnx_dir) / "clinicalbert_int8.onnx"
    fp32_path = Path(onnx_dir) / "clinicalbert_fp32.onnx"

    path = int8_path if int8_path.exists() else (fp32_path if fp32_path.exists() else None)
    if path is None:
        logger.warning("No ClinicalBERT ONNX model found", dir=onnx_dir)
        return None

    try:
        return ClinicalBERTORT(str(path), model_name)
    except Exception as exc:
        logger.error("ClinicalBERT ORT load failed", error=str(exc))
        return None


def load_sentencebert_ort(onnx_dir: str, model_name: str) -> Optional["SentenceBERTORT"]:
    int8_path = Path(onnx_dir) / "sentencebert_int8.onnx"
    fp32_path = Path(onnx_dir) / "sentencebert_fp32.onnx"

    path = int8_path if int8_path.exists() else (fp32_path if fp32_path.exists() else None)
    if path is None:
        logger.warning("No Sentence-BERT ONNX model found", dir=onnx_dir)
        return None

    try:
        return SentenceBERTORT(str(path), model_name)
    except Exception as exc:
        logger.error("Sentence-BERT ORT load failed", error=str(exc))
        return None
