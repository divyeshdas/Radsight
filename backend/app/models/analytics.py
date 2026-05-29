from typing import Optional, List, Dict, Any
from pydantic import Field
from app.models.base import MongoBaseModel


class DailyAnalytics(MongoBaseModel):
    date: str
    total_reports: int = 0
    processed_reports: int = 0
    failed_reports: int = 0

    severity_distribution: Dict[str, int] = Field(default_factory=dict)
    disease_counts: Dict[str, int] = Field(default_factory=dict)
    anatomy_counts: Dict[str, int] = Field(default_factory=dict)
    report_type_counts: Dict[str, int] = Field(default_factory=dict)

    avg_processing_time_ms: float = 0.0
    avg_risk_score: float = 0.0
    avg_confidence: float = 0.0
    critical_cases: int = 0
    flagged_for_review: int = 0

    throughput_per_minute: float = 0.0
    peak_hour: Optional[int] = None


class AnomalyLog(MongoBaseModel):
    anomaly_type: str
    severity: str
    description: str
    detected_at: str

    affected_metric: str
    baseline_value: float
    observed_value: float
    deviation_score: float

    related_diseases: List[str] = Field(default_factory=list)
    related_reports: List[str] = Field(default_factory=list)
    is_resolved: bool = False
    resolution_notes: Optional[str] = None


class ProcessingLog(MongoBaseModel):
    report_id: str
    stage: str
    status: str
    message: Optional[str] = None

    duration_ms: Optional[float] = None
    model_used: Optional[str] = None
    tokens_processed: Optional[int] = None
    error_detail: Optional[str] = None

    metadata: Dict[str, Any] = Field(default_factory=dict)


class EmbeddingRecord(MongoBaseModel):
    report_id: str
    patient_id: str
    model: str = "sentence-bert"
    dimension: int = 768
    faiss_index_id: Optional[int] = None
    summary_used: Optional[str] = None
    cache_key: Optional[str] = None
