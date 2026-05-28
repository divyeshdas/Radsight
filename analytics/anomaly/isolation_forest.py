from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import structlog

logger = structlog.get_logger(__name__)

# Isolation Forest isolates anomalies by building random decision trees.
# Anomalous points have shorter average path lengths because they are
# sparse and require fewer splits to isolate. The anomaly score is
# inversely proportional to the average path length.
# contamination controls the expected proportion of outliers in the data.


FEATURE_COLUMNS = [
    "total_reports",
    "critical_count",
    "critical_rate",
    "avg_risk_score",
    "flagged_count",
    "processing_failures",
]


def _build_feature_matrix(daily_metrics: List[Dict]) -> Tuple[np.ndarray, List[str]]:
    rows = []
    dates = []

    for m in daily_metrics:
        total = max(m.get("total_reports", 0), 1)
        critical = m.get("critical_count", m.get("severity_distribution", {}).get("critical", 0))
        flagged = m.get("flagged_count", m.get("flagged_for_review", 0))
        failures = m.get("processing_failures", total - m.get("processed_reports", total))

        rows.append([
            total,
            critical,
            critical / total,
            m.get("avg_risk_score", 0.0) or 0.0,
            flagged,
            max(failures, 0),
        ])
        dates.append(m.get("date", ""))

    return np.array(rows, dtype=np.float32), dates


def detect_anomalies(
    daily_metrics: List[Dict],
    contamination: float = 0.05,
    n_estimators: int = 100,
) -> Dict:
    if len(daily_metrics) < 10:
        return {
            "anomalies": [],
            "anomaly_count": 0,
            "error": "Need at least 10 data points",
        }

    X, dates = _build_feature_matrix(daily_metrics)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = IsolationForest(
        n_estimators=n_estimators,
        contamination=contamination,
        random_state=42,
        max_samples="auto",
    )
    labels = model.fit_predict(X_scaled)
    scores = model.score_samples(X_scaled)

    anomalies = []
    for i, (label, score, date) in enumerate(zip(labels, scores, dates)):
        if label == -1:
            metrics = daily_metrics[i]
            total = max(metrics.get("total_reports", 1), 1)
            critical = metrics.get("severity_distribution", {}).get("critical", 0)

            anomaly_type = _classify_anomaly(metrics, X[i], scaler, X)
            description = _describe_anomaly(anomaly_type, metrics, X[i])

            anomalies.append({
                "date": date,
                "anomaly_type": anomaly_type,
                "severity": _anomaly_severity(score),
                "description": description,
                "deviation_score": round(float(-score), 4),
                "affected_metric": _identify_affected_metric(X[i], X),
                "baseline_value": round(float(np.median(X[:, 0])), 2),
                "observed_value": float(X[i][0]),
                "metrics_snapshot": {
                    "total_reports": int(X[i][0]),
                    "critical_count": int(X[i][1]),
                    "critical_rate": round(float(X[i][2]), 4),
                    "avg_risk_score": round(float(X[i][3]), 4),
                },
                "is_resolved": False,
            })

    anomaly_dates = {a["date"] for a in anomalies}
    normal_scores = scores[labels == 1]

    return {
        "anomalies": sorted(anomalies, key=lambda x: -x["deviation_score"]),
        "anomaly_count": len(anomalies),
        "total_analyzed": len(daily_metrics),
        "anomaly_rate": round(len(anomalies) / len(daily_metrics) * 100, 2),
        "score_stats": {
            "mean": round(float(np.mean(scores)), 4),
            "threshold": round(float(np.percentile(scores, contamination * 100)), 4),
        },
    }


def _classify_anomaly(metrics: Dict, features: np.ndarray, scaler: StandardScaler, all_features: np.ndarray) -> str:
    baseline_critical_rate = float(np.median(all_features[:, 2]))
    current_critical_rate = float(features[2])

    if current_critical_rate > baseline_critical_rate * 2.5:
        return "critical_surge"

    baseline_total = float(np.median(all_features[:, 0]))
    current_total = float(features[0])

    if current_total > baseline_total * 3.0:
        return "volume_spike"
    if current_total < baseline_total * 0.3:
        return "volume_drop"

    if float(features[4]) > float(np.percentile(all_features[:, 4], 90)):
        return "flagged_surge"

    return "statistical_anomaly"


def _describe_anomaly(anomaly_type: str, metrics: Dict, features: np.ndarray) -> str:
    descriptions = {
        "critical_surge": f"Critical case rate {float(features[2]):.1%} — unusually high. Possible disease outbreak or data quality issue.",
        "volume_spike": f"Report volume {int(features[0])} — significantly above baseline. Possible batch ingestion or real surge.",
        "volume_drop": f"Report volume {int(features[0])} — significantly below baseline. Possible ingestion failure or holiday.",
        "flagged_surge": f"Flagged-for-review count {int(features[4])} — unusually elevated. Manual review queue may be backed up.",
        "statistical_anomaly": "Unusual combination of metrics detected across multiple dimensions.",
    }
    return descriptions.get(anomaly_type, "Anomalous pattern detected.")


def _anomaly_severity(isolation_score: float) -> str:
    if isolation_score < -0.15:
        return "critical"
    if isolation_score < -0.10:
        return "high"
    if isolation_score < -0.05:
        return "moderate"
    return "low"


def _identify_affected_metric(features: np.ndarray, all_features: np.ndarray) -> str:
    z_scores = np.abs((features - np.mean(all_features, axis=0)) / (np.std(all_features, axis=0) + 1e-8))
    most_deviant = int(np.argmax(z_scores))
    return FEATURE_COLUMNS[most_deviant] if most_deviant < len(FEATURE_COLUMNS) else "unknown"


def detect_disease_surge(
    disease_timeseries: List[Dict],
    disease: str,
    window: int = 7,
    threshold_sigma: float = 2.5,
) -> Dict:
    """
    Statistical surge detection using rolling z-score.
    Flags days where the count exceeds mean + threshold_sigma * std
    of the preceding window.
    """
    if len(disease_timeseries) < window + 2:
        return {"surges": [], "disease": disease}

    df = pd.DataFrame(disease_timeseries).sort_values("date")
    counts = df["count"].values.astype(float)
    surges = []

    for i in range(window, len(counts)):
        window_data = counts[i - window:i]
        mu = np.mean(window_data)
        sigma = np.std(window_data)
        z = (counts[i] - mu) / max(sigma, 0.1)

        if z > threshold_sigma:
            surges.append({
                "date": df.iloc[i]["date"],
                "count": int(counts[i]),
                "baseline_mean": round(float(mu), 2),
                "z_score": round(float(z), 3),
                "excess": int(counts[i] - mu),
            })

    return {
        "disease": disease,
        "surges": surges,
        "surge_count": len(surges),
        "window_days": window,
        "threshold_sigma": threshold_sigma,
    }
