from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
import structlog

logger = structlog.get_logger(__name__)

# Prophet uses additive decomposition:
#   y(t) = trend(t) + seasonality(t) + holidays(t) + error(t)
# Trend is modelled as piecewise linear with automatic changepoint detection.
# Seasonality uses Fourier series to capture periodic patterns.
# Fitting uses Stan's L-BFGS MAP estimation.


def _load_prophet():
    try:
        from prophet import Prophet
        return Prophet
    except ImportError:
        logger.warning("Prophet not installed, using statsmodels fallback")
        return None


def forecast_disease_trend(
    daily_counts: List[Dict],
    periods: int = 30,
    seasonality_mode: str = "additive",
    disease: Optional[str] = None,
) -> Dict:
    """
    Forecasts daily report counts for a given disease or overall.
    daily_counts: list of {"date": "YYYY-MM-DD", "count": int}
    Returns forecast with yhat, yhat_lower, yhat_upper for `periods` days ahead.
    """
    if len(daily_counts) < 10:
        return {"error": "Not enough data for forecasting (minimum 10 data points)", "forecast": []}

    df = pd.DataFrame(daily_counts)
    df = df.rename(columns={"date": "ds", "count": "y"})
    df["ds"] = pd.to_datetime(df["ds"])
    df = df.sort_values("ds").drop_duplicates("ds")
    df["y"] = df["y"].clip(lower=0)

    Prophet = _load_prophet()
    if Prophet is None:
        return _statsmodels_forecast(df, periods)

    try:
        model = Prophet(
            seasonality_mode=seasonality_mode,
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            changepoint_prior_scale=0.05,
            seasonality_prior_scale=10.0,
            interval_width=0.95,
        )
        model.fit(df)

        future = model.make_future_dataframe(periods=periods)
        forecast = model.predict(future)

        forecast_rows = forecast[["ds", "yhat", "yhat_lower", "yhat_upper", "trend"]].tail(periods)
        result = []
        for _, row in forecast_rows.iterrows():
            result.append({
                "date": row["ds"].strftime("%Y-%m-%d"),
                "forecast": round(max(float(row["yhat"]), 0), 2),
                "lower": round(max(float(row["yhat_lower"]), 0), 2),
                "upper": round(max(float(row["yhat_upper"]), 0), 2),
                "trend": round(float(row["trend"]), 2),
            })

        changepoints = [str(cp.date()) for cp in model.changepoints[-5:]]

        return {
            "disease": disease or "all",
            "forecast": result,
            "periods": periods,
            "training_points": len(df),
            "changepoints": changepoints,
            "seasonality_mode": seasonality_mode,
        }

    except Exception as e:
        logger.error("Prophet forecasting failed", error=str(e))
        return _statsmodels_forecast(df, periods)


def _statsmodels_forecast(df: pd.DataFrame, periods: int) -> Dict:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    try:
        series = df.set_index("ds")["y"]
        model = ExponentialSmoothing(
            series,
            trend="add",
            seasonal="add" if len(series) >= 14 else None,
            seasonal_periods=7,
        ).fit(optimized=True)

        forecast_values = model.forecast(periods)
        result = []
        last_date = df["ds"].max()
        for i, val in enumerate(forecast_values):
            date = last_date + timedelta(days=i + 1)
            yhat = max(float(val), 0)
            result.append({
                "date": date.strftime("%Y-%m-%d"),
                "forecast": round(yhat, 2),
                "lower": round(yhat * 0.8, 2),
                "upper": round(yhat * 1.2, 2),
                "trend": round(yhat, 2),
            })

        return {
            "disease": "all",
            "forecast": result,
            "periods": periods,
            "training_points": len(df),
            "method": "exponential_smoothing_fallback",
        }
    except Exception as e:
        logger.error("Statsmodels fallback also failed", error=str(e))
        return {"error": str(e), "forecast": []}


def forecast_severity_distribution(
    daily_severity: List[Dict],
    periods: int = 14,
) -> Dict:
    """
    Forecasts the proportion of critical/high severity cases over time.
    daily_severity: [{"date": ..., "critical": int, "high": int, "total": int}]
    """
    if len(daily_severity) < 7:
        return {"error": "Insufficient data", "forecast": []}

    df = pd.DataFrame(daily_severity)
    df["ds"] = pd.to_datetime(df["date"])
    df["y"] = df["critical"] / df["total"].clip(lower=1)
    df = df[["ds", "y"]].sort_values("ds")

    Prophet = _load_prophet()
    if Prophet is None:
        return {"error": "Prophet unavailable", "forecast": []}

    try:
        model = Prophet(
            seasonality_mode="multiplicative",
            changepoint_prior_scale=0.1,
            interval_width=0.90,
        )
        model.fit(df)
        future = model.make_future_dataframe(periods=periods)
        forecast = model.predict(future)
        rows = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(periods)

        return {
            "metric": "critical_case_rate",
            "forecast": [
                {
                    "date": row["ds"].strftime("%Y-%m-%d"),
                    "rate": round(float(np.clip(row["yhat"], 0, 1)), 4),
                    "lower": round(float(np.clip(row["yhat_lower"], 0, 1)), 4),
                    "upper": round(float(np.clip(row["yhat_upper"], 0, 1)), 4),
                }
                for _, row in rows.iterrows()
            ],
            "periods": periods,
        }
    except Exception as e:
        return {"error": str(e), "forecast": []}
