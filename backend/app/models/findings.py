from enum import Enum
from typing import Optional, List
from pydantic import Field
from app.models.base import MongoBaseModel


class FindingCategory(str, Enum):
    abnormality = "abnormality"
    disease = "disease"
    symptom = "symptom"
    anatomy = "anatomy"
    procedure = "procedure"
    measurement = "measurement"


class FindingSeverity(str, Enum):
    mild = "mild"
    moderate = "moderate"
    severe = "severe"
    critical = "critical"


class ExtractedFinding(MongoBaseModel):
    report_id: str
    patient_id: str

    category: FindingCategory
    disease: Optional[str] = None
    anatomy: Optional[str] = None
    symptoms: List[str] = Field(default_factory=list)
    severity: Optional[FindingSeverity] = None

    finding_text: str
    normalized_term: Optional[str] = None
    icd10_code: Optional[str] = None
    snomed_code: Optional[str] = None

    confidence: float = Field(ge=0.0, le=1.0)
    source_model: str = "biobert"
    char_start: Optional[int] = None
    char_end: Optional[int] = None

    laterality: Optional[str] = None
    acuity: Optional[str] = None
    negated: bool = False
    uncertain: bool = False


class NLPEntity(MongoBaseModel):
    report_id: str
    entity_text: str
    entity_type: str
    label: str
    start: int
    end: int
    confidence: float = Field(ge=0.0, le=1.0)
    source: str = "scispacy"


class SeverityScore(MongoBaseModel):
    report_id: str
    patient_id: str

    overall_score: float = Field(ge=0.0, le=1.0)
    risk_level: str
    urgency_score: float = Field(ge=0.0, le=1.0)
    complexity_score: float = Field(ge=0.0, le=1.0)

    component_scores: dict = Field(default_factory=dict)
    critical_findings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)

    model_version: str = "v1.0"
    explainability: dict = Field(default_factory=dict)
