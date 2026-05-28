from typing import List, Dict, Optional
import numpy as np
import pandas as pd
import structlog

logger = structlog.get_logger(__name__)


def compute_moving_average(
    series: List[float],
    window: int = 7,
) -> List[Optional[float]]:
    result = []
    for i in range(len(series)):
        if i < window - 1:
            result.append(None)
        else:
            result.append(round(float(np.mean(series[i - window + 1:i + 1])), 4))
    return result


def compute_ewma(series: List[float], alpha: float = 0.3) -> List[float]:
    """
    Exponentially Weighted Moving Average.
    alpha controls smoothing: higher alpha = more weight to recent values.
    Each value: ewma[t] = alpha * x[t] + (1 - alpha) * ewma[t-1]
    """
    if not series:
        return []
    result = [series[0]]
    for val in series[1:]:
        result.append(alpha * val + (1 - alpha) * result[-1])
    return [round(v, 4) for v in result]


def compute_trend_slope(series: List[float], window: int = 14) -> List[Optional[float]]:
    """
    Rolling linear regression slope over `window` points.
    Positive = upward trend, negative = downward trend.
    """
    result = []
    for i in range(len(series)):
        if i < window - 1:
            result.append(None)
        else:
            y = np.array(series[i - window + 1:i + 1])
            x = np.arange(len(y), dtype=float)
            if np.std(y) < 1e-10:
                result.append(0.0)
            else:
                slope = float(np.polyfit(x, y, 1)[0])
                result.append(round(slope, 4))
    return result


def compute_daily_trends(
    daily_metrics: List[Dict],
    window: int = 7,
) -> Dict:
    if not daily_metrics:
        return {}

    df = pd.DataFrame(daily_metrics).sort_values("date")
    dates = df["date"].tolist()

    total_series = df.get("total_reports", pd.Series([0] * len(df))).fillna(0).tolist()
    risk_series = df.get("avg_risk_score", pd.Series([0.0] * len(df))).fillna(0).tolist()
    critical_series = [
        row.get("severity_distribution", {}).get("critical", 0)
        for row in daily_metrics
    ]

    ma_total = compute_moving_average(total_series, window)
    ewma_total = compute_ewma(total_series, alpha=0.3)
    slope_total = compute_trend_slope(total_series, window)

    ma_risk = compute_moving_average(risk_series, window)
    ewma_risk = compute_ewma(risk_series, alpha=0.3)

    ma_critical = compute_moving_average(critical_series, window)

    trend_rows = []
    for i, date in enumerate(dates):
        trend_rows.append({
            "date": date,
            "total_reports": total_series[i],
            "ma_total": ma_total[i],
            "ewma_total": ewma_total[i],
            "trend_slope": slope_total[i],
            "avg_risk_score": risk_series[i],
            "ma_risk": ma_risk[i],
            "ewma_risk": ewma_risk[i],
            "critical_count": critical_series[i],
            "ma_critical": ma_critical[i],
        })

    direction = _compute_trend_direction(ewma_total, window)
    current_velocity = slope_total[-1] if slope_total[-1] is not None else 0.0

    return {
        "trend_data": trend_rows,
        "window": window,
        "direction": direction,
        "current_velocity": current_velocity,
        "summary": _build_trend_summary(total_series, critical_series, direction),
    }


def compute_disease_prevalence_trends(
    daily_disease_counts: List[Dict],
    top_n: int = 8,
    window: int = 7,
) -> Dict:
    """
    Computes rolling prevalence trends per disease.
    daily_disease_counts: [{"date": ..., "disease_counts": {"pneumonia": 5, ...}}]
    """
    if not daily_disease_counts:
        return {}

    all_diseases: Dict[str, List] = {}
    dates = []

    for row in sorted(daily_disease_counts, key=lambda x: x["date"]):
        dates.append(row["date"])
        counts = row.get("disease_counts", {})
        for disease, count in counts.items():
            if disease not in all_diseases:
                all_diseases[disease] = []
            all_diseases[disease].append(count)

        for disease in list(all_diseases.keys()):
            if len(all_diseases[disease]) < len(dates):
                all_diseases[disease].append(0)

    totals = {d: sum(v) for d, v in all_diseases.items()}
    top_diseases = sorted(totals, key=lambda d: -totals[d])[:top_n]

    result = {}
    for disease in top_diseases:
        series = all_diseases[disease]
        result[disease] = {
            "dates": dates,
            "counts": series,
            "ma": compute_moving_average(series, window),
            "ewma": compute_ewma(series, alpha=0.3),
            "total": totals[disease],
            "trend": _compute_trend_direction(series, window),
        }

    return {"diseases": result, "top_n": top_n, "window": window}


def compute_rolling_risk_heatmap(
    daily_metrics: List[Dict],
    window: int = 30,
) -> List[Dict]:
    rows = []
    for i, m in enumerate(daily_metrics):
        sev = m.get("severity_distribution", {})
        total = max(sum(sev.values()), 1) if sev else 1

        rows.append({
            "date": m.get("date"),
            "normal_pct": round(sev.get("normal", 0) / total * 100, 1),
            "mild_pct": round(sev.get("mild", 0) / total * 100, 1),
            "moderate_pct": round(sev.get("moderate", 0) / total * 100, 1),
            "high_pct": round(sev.get("high", sev.get("severe", 0)) / total * 100, 1),
            "critical_pct": round(sev.get("critical", 0) / total * 100, 1),
            "risk_index": round(
                (sev.get("moderate", 0) * 0.3 +
                 sev.get("high", sev.get("severe", 0)) * 0.6 +
                 sev.get("critical", 0) * 1.0) / total, 4
            ),
        })
    return rows


def _compute_trend_direction(series: List[float], window: int) -> str:
    if len(series) < window:
        return "insufficient_data"

    recent = series[-window:]
    older = series[-window * 2:-window] if len(series) >= window * 2 else series[:max(len(series) - window, 1)]

    if not older:
        return "stable"

    recent_mean = np.mean(recent)
    older_mean = np.mean(older)

    if older_mean == 0:
        return "stable"

    pct_change = (recent_mean - older_mean) / older_mean

    if pct_change > 0.15:
        return "increasing"
    if pct_change < -0.15:
        return "decreasing"
    return "stable"


def _build_trend_summary(
    total_series: List[float],
    critical_series: List[float],
    direction: str,
) -> Dict:
    recent_7 = total_series[-7:] if len(total_series) >= 7 else total_series
    prior_7 = total_series[-14:-7] if len(total_series) >= 14 else total_series[:-7]

    pct_change = 0.0
    if prior_7 and np.mean(prior_7) > 0:
        pct_change = (np.mean(recent_7) - np.mean(prior_7)) / np.mean(prior_7) * 100

    return {
        "direction": direction,
        "week_over_week_pct": round(float(pct_change), 2),
        "recent_avg_daily": round(float(np.mean(recent_7)), 1) if recent_7 else 0,
        "peak_day": int(np.max(total_series)) if total_series else 0,
        "critical_7day_total": int(sum(critical_series[-7:])) if len(critical_series) >= 7 else 0,
    }
