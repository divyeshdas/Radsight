import random
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Callable
import numpy as np

from datasets.generators.report_generator import SyntheticReportGenerator
from datasets.generators.disease_config import DISEASE_MAP


class TrendGenerator:
    """
    Injects temporal trends into synthetic report streams.

    Supports disease spikes, seasonal patterns, and gradual drift.
    These patterns feed the forecasting and anomaly detection engines.
    """

    def __init__(self, seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed)
        self.report_gen = SyntheticReportGenerator(seed=seed)

    def _date_range(self, start: datetime, end: datetime, step_days: float = 1.0) -> List[datetime]:
        dates = []
        current = start
        delta = timedelta(days=step_days)
        while current <= end:
            dates.append(current)
            current += delta
        return dates

    def generate_spike(
        self,
        disease: str,
        spike_start: datetime,
        spike_duration_days: int = 14,
        baseline_daily: int = 10,
        peak_multiplier: float = 4.0,
    ) -> List[Dict]:
        """
        Simulates a disease outbreak spike using a Gaussian envelope.
        Peak occurs at the midpoint of the spike window.
        """
        dates = self._date_range(spike_start, spike_start + timedelta(days=spike_duration_days))
        mid = spike_duration_days / 2
        sigma = spike_duration_days / 6

        reports = []
        for i, date in enumerate(dates):
            gaussian = np.exp(-0.5 * ((i - mid) / sigma) ** 2)
            daily_count = int(baseline_daily * (1 + (peak_multiplier - 1) * gaussian))

            for _ in range(daily_count):
                r = self.report_gen.generate_report(
                    report_date=date + timedelta(hours=random.uniform(0, 23)),
                    force_disease=disease,
                )
                reports.append(r)

        return reports

    def generate_seasonal_pattern(
        self,
        disease: str,
        year: int,
        peak_months: List[int],
        baseline_monthly: int = 150,
        seasonal_amplitude: float = 0.6,
    ) -> List[Dict]:
        """
        Generates seasonal disease patterns using sine-based modulation.
        peak_months defines which months see the highest prevalence.
        """
        start = datetime(year, 1, 1, tzinfo=timezone.utc)
        end = datetime(year, 12, 31, tzinfo=timezone.utc)
        dates = self._date_range(start, end)

        reports = []
        for date in dates:
            month = date.month
            seasonal_factor = 1.0
            for pm in peak_months:
                distance = min(abs(month - pm), 12 - abs(month - pm))
                seasonal_factor += seasonal_amplitude * np.exp(-0.5 * (distance / 1.5) ** 2)

            daily_baseline = baseline_monthly / 30
            daily_count = int(self.rng.poisson(daily_baseline * seasonal_factor))

            for _ in range(daily_count):
                r = self.report_gen.generate_report(
                    report_date=date + timedelta(hours=random.uniform(0, 23)),
                    force_disease=disease,
                )
                reports.append(r)

        return reports

    def generate_critical_surge(
        self,
        surge_start: datetime,
        duration_days: int = 7,
        daily_critical: int = 15,
    ) -> List[Dict]:
        """
        Simulates a sudden surge in critical-severity cases across all diseases.
        Used to stress-test anomaly detection.
        """
        reports = []
        for day in range(duration_days):
            date = surge_start + timedelta(days=day)
            decay = np.exp(-0.15 * day)
            count = int(daily_critical * (1 + decay))

            for _ in range(count):
                disease = random.choice([d for d in DISEASE_MAP if d != "normal"])
                r = self.report_gen.generate_report(
                    report_date=date + timedelta(hours=random.uniform(0, 23)),
                    force_disease=disease,
                    force_severity="critical",
                )
                reports.append(r)

        return reports

    def generate_gradual_drift(
        self,
        disease: str,
        start: datetime,
        end: datetime,
        start_daily: int = 5,
        end_daily: int = 25,
    ) -> List[Dict]:
        """
        Linear drift in disease prevalence over time.
        Simulates gradual regional increase for trend analysis.
        """
        dates = self._date_range(start, end)
        n = len(dates)
        reports = []

        for i, date in enumerate(dates):
            progress = i / max(n - 1, 1)
            daily_count = int(start_daily + (end_daily - start_daily) * progress)
            daily_count = max(1, int(self.rng.poisson(daily_count)))

            for _ in range(daily_count):
                r = self.report_gen.generate_report(
                    report_date=date + timedelta(hours=random.uniform(0, 23)),
                    force_disease=disease,
                )
                reports.append(r)

        return reports

    def generate_full_simulation(
        self,
        total_reports: int = 50000,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        include_spikes: bool = True,
        include_seasonal: bool = True,
    ) -> List[Dict]:
        """
        Generates a realistic mixed dataset with background baseline +
        disease spikes + seasonal patterns.
        """
        if start_date is None:
            start_date = datetime.now(timezone.utc) - timedelta(days=730)
        if end_date is None:
            end_date = datetime.now(timezone.utc)

        baseline_count = total_reports
        spike_reports = []
        seasonal_reports = []

        if include_spikes:
            mid = start_date + (end_date - start_date) / 2
            spike_reports = self.generate_spike(
                disease="pneumonia",
                spike_start=mid,
                spike_duration_days=21,
                baseline_daily=8,
                peak_multiplier=5.0,
            )
            spike_reports += self.generate_critical_surge(
                surge_start=mid + timedelta(days=45),
                duration_days=5,
                daily_critical=20,
            )
            baseline_count = max(0, total_reports - len(spike_reports))

        if include_seasonal:
            year = start_date.year
            seasonal_reports = self.generate_seasonal_pattern(
                disease="pulmonary edema",
                year=year,
                peak_months=[1, 2, 12],
                baseline_monthly=100,
                seasonal_amplitude=0.7,
            )
            baseline_count = max(0, baseline_count - len(seasonal_reports))

        baseline_reports = self.report_gen.generate_batch(
            count=baseline_count,
            start_date=start_date,
            end_date=end_date,
        )

        all_reports = baseline_reports + spike_reports + seasonal_reports
        all_reports.sort(key=lambda r: r["created_at"])
        return all_reports
