import re
import time
import torch
import torch.nn.functional as F
from typing import Dict, List, Tuple
from core.model_registry import registry
import structlog

logger = structlog.get_logger(__name__)

LABELS = ["normal", "abnormal", "critical"]

CRITICAL_KEYWORDS = [
    "tension pneumothorax", "massive hemorrhage", "acute respiratory failure",
    "critical", "life-threatening", "immediate", "urgent intervention",
    "cardiac tamponade", "massive pulmonary embolism", "aortic dissection",
]

ABNORMAL_KEYWORDS = [
    "pneumonia", "effusion", "edema", "consolidation", "infiltrate",
    "cardiomegaly", "atelectasis", "nodule", "mass", "fracture",
    "opacity", "fibrosis", "emphysema", "pneumothorax", "lesion",
]

NORMAL_KEYWORDS = [
    "no acute", "clear", "unremarkable", "within normal limits",
    "no evidence", "no focal", "normal", "no pneumothorax",
    "no effusion", "no infiltrate",
]


def _rule_based_classify(text: str) -> Tuple[str, float, Dict[str, float]]:
    text_lower = text.lower()

    critical_score = sum(1 for kw in CRITICAL_KEYWORDS if kw in text_lower)
    abnormal_score = sum(1 for kw in ABNORMAL_KEYWORDS if kw in text_lower)
    normal_score = sum(1 for kw in NORMAL_KEYWORDS if kw in text_lower)

    if critical_score >= 1:
        confidence = min(0.75 + critical_score * 0.05, 0.95)
        return "critical", confidence, {"normal": 0.05, "abnormal": 0.15, "critical": confidence}

    if abnormal_score > normal_score:
        ratio = abnormal_score / max(abnormal_score + normal_score, 1)
        confidence = min(0.60 + ratio * 0.25, 0.90)
        return "abnormal", confidence, {"normal": 1 - confidence, "abnormal": confidence, "critical": 0.05}

    if normal_score > 0:
        confidence = min(0.65 + normal_score * 0.05, 0.92)
        return "normal", confidence, {"normal": confidence, "abnormal": 1 - confidence, "critical": 0.02}

    return "abnormal", 0.55, {"normal": 0.30, "abnormal": 0.55, "critical": 0.15}


def _model_based_classify(text: str) -> Tuple[str, float, Dict[str, float]]:
    ort_session = registry.ort_clinicalbert
    if ort_session is not None:
        try:
            pred_label, confidence, scores = ort_session.predict_one(" ".join(text.split()[:400]))
            return pred_label, confidence, scores
        except Exception as e:
            logger.warning("ORT classification failed, falling back to PyTorch", error=str(e))

    tokenizer, model = registry.load_clinicalbert()

    truncated = " ".join(text.split()[:400])
    inputs = tokenizer(
        truncated,
        return_tensors="pt",
        truncation=True,
        max_length=512,
        padding=True,
    )

    with torch.no_grad():
        outputs = model(**inputs)

    probs = F.softmax(outputs.logits, dim=-1).squeeze()
    prob_list = probs.tolist()

    if len(prob_list) != 3:
        prob_list = [prob_list[0] if prob_list else 0.33] * 3

    scores = {label: round(float(p), 4) for label, p in zip(LABELS, prob_list)}
    pred_label = max(scores, key=scores.get)
    confidence = scores[pred_label]

    return pred_label, confidence, scores


def classify_report(text: str, use_model: bool = True) -> Dict:
    t0 = time.perf_counter()

    rule_label, rule_conf, rule_scores = _rule_based_classify(text)

    if use_model and len(text.split()) >= 15:
        try:
            model_label, model_conf, model_scores = _model_based_classify(text)
            if model_conf > 0.70:
                final_label = model_label
                final_conf = model_conf * 0.6 + rule_conf * 0.4
                blended = {
                    k: round(model_scores[k] * 0.6 + rule_scores.get(k, 0) * 0.4, 4)
                    for k in LABELS
                }
            else:
                final_label = rule_label
                final_conf = rule_conf
                blended = rule_scores
        except Exception as e:
            logger.warning("Model classification failed, using rule-based", error=str(e))
            final_label = rule_label
            final_conf = rule_conf
            blended = rule_scores
    else:
        final_label = rule_label
        final_conf = rule_conf
        blended = rule_scores

    elapsed_ms = (time.perf_counter() - t0) * 1000

    urgency_map = {"normal": "routine", "abnormal": "standard", "critical": "urgent"}

    return {
        "classification": final_label,
        "confidence": round(final_conf, 4),
        "scores": blended,
        "urgency": urgency_map[final_label],
        "inference_ms": round(elapsed_ms, 2),
        "explainability": {
            "rule_label": rule_label,
            "rule_confidence": round(rule_conf, 4),
            "critical_keywords_found": [kw for kw in CRITICAL_KEYWORDS if kw in text.lower()],
            "abnormal_keywords_found": [kw for kw in ABNORMAL_KEYWORDS if kw in text.lower()][:5],
        },
    }


def classify_batch(texts: List[str], batch_size: int = 16) -> List[Dict]:
    """
    Classify a list of reports in batches. Uses ORT batch inference when available
    (single tokenizer call + single forward pass per chunk) instead of N sequential calls.
    """
    ort_session = registry.ort_clinicalbert
    if ort_session is None:
        return [classify_report(text) for text in texts]

    results = []
    for i in range(0, len(texts), batch_size):
        chunk = texts[i:i + batch_size]
        truncated = [" ".join(t.split()[:400]) for t in chunk]

        try:
            probs_matrix = ort_session.predict_batch(truncated)
        except Exception as exc:
            logger.warning("ORT batch failed, falling back", error=str(exc))
            results.extend([classify_report(t) for t in chunk])
            continue

        for j, text in enumerate(chunk):
            prob_row = probs_matrix[j]
            scores = {label: round(float(p), 4) for label, p in zip(LABELS, prob_row)}
            model_label = max(scores, key=scores.__getitem__)
            model_conf = scores[model_label]

            rule_label, rule_conf, rule_scores = _rule_based_classify(text)

            if model_conf > 0.70:
                final_label = model_label
                final_conf = model_conf * 0.6 + rule_conf * 0.4
                blended = {
                    k: round(scores[k] * 0.6 + rule_scores.get(k, 0) * 0.4, 4)
                    for k in LABELS
                }
            else:
                final_label = rule_label
                final_conf = rule_conf
                blended = rule_scores

            urgency_map = {"normal": "routine", "abnormal": "standard", "critical": "urgent"}
            results.append({
                "classification": final_label,
                "confidence": round(final_conf, 4),
                "scores": blended,
                "urgency": urgency_map[final_label],
                "inference_ms": 0.0,
                "explainability": {
                    "rule_label": rule_label,
                    "rule_confidence": round(rule_conf, 4),
                    "critical_keywords_found": [kw for kw in CRITICAL_KEYWORDS if kw in text.lower()],
                    "abnormal_keywords_found": [kw for kw in ABNORMAL_KEYWORDS if kw in text.lower()][:5],
                },
            })

    return results
