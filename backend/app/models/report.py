from enum import Enum
from typing import Optional, List
from pydantic import Field
from app.models.base import MongoBaseModel


class ReportType(str, Enum):
    chest_xray = "chest_xray"
    ct_scan = "ct_scan"
    mri = "mri"
    ultrasound = "ultrasound"
    mammogram = "mammogram"
    other = "other"


class ReportStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class SeverityLevel(str, Enum):
    normal = "normal"
    low = "low"
    moderate = "moderate"
    high = "high"
    critical = "critical"


class ReportSource(str, Enum):
    upload = "upload"
    ocr = "ocr"
    synthetic = "synthetic"
    api = "api"


class RadiologyReport(MongoBaseModel):
    patient_id: str = Field(min_length=3, max_length=50)
    report_type: ReportType = ReportType.chest_xray
    source: ReportSource = ReportSource.upload
    status: ReportStatus = ReportStatus.pending

    raw_text: str
    cleaned_text: Optional[str] = None
    word_count: int = 0

    severity: Optional[SeverityLevel] = None
    risk_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    classification_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    ai_summary: Optional[str] = None

    findings_count: int = 0
    has_critical_findings: bool = False
    flagged_for_review: bool = False

    modality: Optional[str] = None
    body_region: Optional[str] = None
    institution: Optional[str] = None
    radiologist_id: Optional[str] = None

    processing_time_ms: Optional[float] = None
    ocr_confidence: Optional[float] = None

    tags: List[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class ReportUploadRequest(MongoBaseModel):
    patient_id: str
    report_type: ReportType = ReportType.chest_xray
    institution: Optional[str] = None
    radiologist_id: Optional[str] = None
    metadata: dict = Field(default_factory=dict)
