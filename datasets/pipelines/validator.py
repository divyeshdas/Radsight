from typing import List, Dict, Tuple
from datasets.generators.disease_config import DISEASE_MAP


REQUIRED_FIELDS = [
    "patient_id", "report_type", "source", "status",
    "raw_text", "severity", "risk_score", "created_at",
]

VALID_REPORT_TYPES = {"chest_xray", "ct_scan", "mri", "ultrasound", "mammogram", "other"}
VALID_SEVERITIES = {"normal", "mild", "moderate", "severe", "critical"}
VALID_STATUSES = {"pending", "processing", "completed", "failed"}


def validate_report(report: Dict) -> Tuple[bool, List[str]]:
    errors = []

    for field in REQUIRED_FIELDS:
        if field not in report or report[field] is None:
            errors.append(f"Missing required field: {field}")

    if "report_type" in report and report["report_type"] not in VALID_REPORT_TYPES:
        errors.append(f"Invalid report_type: {report['report_type']}")

    if "severity" in report and report["severity"] and report["severity"] not in VALID_SEVERITIES:
        errors.append(f"Invalid severity: {report['severity']}")

    if "status" in report and report["status"] not in VALID_STATUSES:
        errors.append(f"Invalid status: {report['status']}")

    if "risk_score" in report and report["risk_score"] is not None:
        score = report["risk_score"]
        if not isinstance(score, (int, float)) or not (0.0 <= score <= 1.0):
            errors.append(f"risk_score must be between 0 and 1, got: {score}")

    if "raw_text" in report and isinstance(report["raw_text"], str):
        if len(report["raw_text"].strip()) < 10:
            errors.append("raw_text is too short (< 10 chars)")

    if "patient_id" in report and isinstance(report["patient_id"], str):
        if len(report["patient_id"]) < 3:
            errors.append("patient_id too short")

    return len(errors) == 0, errors


def validate_batch(reports: List[Dict]) -> Dict:
    valid = []
    invalid = []
    error_summary: Dict[str, int] = {}

    for i, report in enumerate(reports):
        ok, errors = validate_report(report)
        if ok:
            valid.append(report)
        else:
            invalid.append({"index": i, "errors": errors})
            for e in errors:
                error_summary[e] = error_summary.get(e, 0) + 1

    return {
        "total": len(reports),
        "valid": len(valid),
        "invalid": len(invalid),
        "valid_reports": valid,
        "invalid_reports": invalid,
        "error_summary": error_summary,
        "pass_rate": round(len(valid) / max(len(reports), 1) * 100, 2),
    }


def compute_dataset_stats(reports: List[Dict]) -> Dict:
    if not reports:
        return {}

    severity_dist: Dict[str, int] = {}
    disease_dist: Dict[str, int] = {}
    risk_scores = []
    confidences = []
    word_counts = []

    for r in reports:
        sev = r.get("severity", "unknown")
        severity_dist[sev] = severity_dist.get(sev, 0) + 1

        disease = r.get("metadata", {}).get("disease", "unknown")
        disease_dist[disease] = disease_dist.get(disease, 0) + 1

        if r.get("risk_score") is not None:
            risk_scores.append(r["risk_score"])
        if r.get("classification_confidence") is not None:
            confidences.append(r["classification_confidence"])
        if r.get("word_count"):
            word_counts.append(r["word_count"])

    import numpy as np

    return {
        "total_reports": len(reports),
        "severity_distribution": severity_dist,
        "disease_distribution": disease_dist,
        "risk_score_stats": {
            "mean": round(float(np.mean(risk_scores)), 4) if risk_scores else None,
            "std": round(float(np.std(risk_scores)), 4) if risk_scores else None,
            "min": round(float(np.min(risk_scores)), 4) if risk_scores else None,
            "max": round(float(np.max(risk_scores)), 4) if risk_scores else None,
        },
        "confidence_stats": {
            "mean": round(float(np.mean(confidences)), 4) if confidences else None,
            "std": round(float(np.std(confidences)), 4) if confidences else None,
        },
        "word_count_stats": {
            "mean": round(float(np.mean(word_counts)), 1) if word_counts else None,
            "min": int(np.min(word_counts)) if word_counts else None,
            "max": int(np.max(word_counts)) if word_counts else None,
        },
        "critical_cases": severity_dist.get("critical", 0),
        "flagged_count": sum(1 for r in reports if r.get("flagged_for_review")),
    }
