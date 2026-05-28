import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
import numpy as np

from datasets.generators.disease_config import (
    DISEASE_REGISTRY, DISEASE_MAP, SEVERITY_TO_RISK,
    REPORT_TEMPLATES, NORMAL_PHRASES, CARDIAC_DESCRIPTORS, MEDIASTINUM_DESCRIPTORS,
    DiseaseDefinition,
)


class SyntheticReportGenerator:
    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        self._disease_names = [d.name for d in DISEASE_REGISTRY]
        self._disease_weights = np.array([d.prevalence_weight for d in DISEASE_REGISTRY])
        self._disease_weights /= self._disease_weights.sum()

        self._report_types = ["chest_xray", "ct_scan", "mri", "ultrasound"]
        self._report_type_weights = [0.55, 0.25, 0.12, 0.08]

        self._institutions = [
            "Memorial General Hospital", "St. Catherine Medical Center",
            "Riverside Radiology Associates", "Northside University Hospital",
            "Bay Area Imaging Center", "Lakewood Regional Medical",
            "Summit Health Radiology", "Oceanview Diagnostic Center",
        ]

        self._modalities = {
            "chest_xray": ["PA/Lateral", "AP Portable", "PA only"],
            "ct_scan": ["CT w/ contrast", "CT w/o contrast", "CT w/ and w/o contrast"],
            "mri": ["MRI w/ contrast", "MRI w/o contrast"],
            "ultrasound": ["Ultrasound guided", "Diagnostic ultrasound"],
        }

    def _pick_disease(self) -> DiseaseDefinition:
        idx = np.random.choice(len(self._disease_names), p=self._disease_weights)
        return DISEASE_REGISTRY[idx]

    def _pick_severity(self, disease: DiseaseDefinition) -> str:
        if disease.name == "normal":
            return "normal"
        weights = disease.severity_weights
        return random.choices(list(weights.keys()), weights=list(weights.values()), k=1)[0]

    def _generate_finding_text(self, disease: DiseaseDefinition, severity: str, anatomy: str) -> str:
        finding = random.choice(disease.typical_findings)
        size_descriptors = {
            "mild": ["small", "minimal", "trace", "subtle"],
            "moderate": ["moderate", "moderate-sized", "moderate amount of"],
            "severe": ["large", "substantial", "extensive", "significant"],
            "critical": ["massive", "critical", "life-threatening", "severe"],
        }
        size = random.choice(size_descriptors.get(severity, ["moderate"]))

        templates = [
            f"{size.capitalize()} {disease.name} is identified in the {anatomy}.",
            f"There is {size} {disease.name} noted involving the {anatomy}.",
            f"{finding.capitalize()} consistent with {size} {disease.name} in the {anatomy}.",
            f"Findings are consistent with {size} {disease.name} affecting the {anatomy}.",
            f"The {anatomy} demonstrates {finding}, compatible with {size} {disease.name}.",
        ]
        return random.choice(templates)

    def _generate_impression(self, disease: DiseaseDefinition, severity: str, anatomy: str) -> str:
        if disease.name == "normal":
            return f"IMPRESSION: {random.choice(NORMAL_PHRASES)}"

        risk_level, _, _ = SEVERITY_TO_RISK.get(severity, ("moderate", 0.35, 0.60))
        urgency_phrases = {
            "low":      "Recommend outpatient follow-up.",
            "moderate": "Clinical correlation recommended.",
            "high":     "Prompt clinical evaluation advised.",
            "critical": "Urgent clinical attention required.",
        }

        rec = random.choice(disease.recommendations)
        urgency = urgency_phrases.get(risk_level, "Clinical correlation recommended.")
        return f"IMPRESSION: {disease.normalized.capitalize()} in the {anatomy}. {rec}. {urgency}"

    def _build_report_text(
        self,
        disease: DiseaseDefinition,
        severity: str,
        anatomy: str,
        report_type: str,
    ) -> str:
        templates = REPORT_TEMPLATES.get(report_type, REPORT_TEMPLATES["chest_xray"])
        template = random.choice(templates)

        if disease.name == "normal":
            findings = random.choice(NORMAL_PHRASES) + " "
        else:
            findings = self._generate_finding_text(disease, severity, anatomy) + " "

        cardiac_key = severity if severity in CARDIAC_DESCRIPTORS else "normal"
        cardiac = random.choice(CARDIAC_DESCRIPTORS[cardiac_key])

        mediastinum_key = "abnormal" if severity in ("severe", "critical") and random.random() < 0.3 else "normal"
        mediastinum = random.choice(MEDIASTINUM_DESCRIPTORS[mediastinum_key])

        osseous_options = ["intact", "unremarkable", "no acute fracture", "within normal limits"]
        osseous = random.choice(osseous_options)

        impression = self._generate_impression(disease, severity, anatomy)

        return template.format(
            findings=findings,
            cardiac=cardiac,
            mediastinum=mediastinum,
            osseous=osseous,
            impression=impression,
        )

    def _compute_risk_score(self, severity: str) -> float:
        _, low, high = SEVERITY_TO_RISK.get(severity, ("moderate", 0.35, 0.60))
        score = np.random.uniform(low, high)
        noise = np.random.normal(0, 0.02)
        return float(np.clip(score + noise, 0.0, 1.0))

    def _compute_confidence(self) -> float:
        return float(np.clip(np.random.beta(8, 2), 0.65, 0.99))

    def generate_report(
        self,
        patient_id: Optional[str] = None,
        report_date: Optional[datetime] = None,
        force_disease: Optional[str] = None,
        force_severity: Optional[str] = None,
    ) -> Dict:
        disease = DISEASE_MAP.get(force_disease) if force_disease else self._pick_disease()
        severity = force_severity if force_severity else self._pick_severity(disease)
        anatomy = random.choice(disease.anatomy)
        report_type = random.choices(self._report_types, weights=self._report_type_weights, k=1)[0]

        raw_text = self._build_report_text(disease, severity, anatomy, report_type)
        risk_score = self._compute_risk_score(severity)
        confidence = self._compute_confidence()
        risk_level, _, _ = SEVERITY_TO_RISK.get(severity, ("moderate", 0.35, 0.60))

        if report_date is None:
            report_date = datetime.now(timezone.utc)

        if patient_id is None:
            patient_id = f"PT-{uuid.uuid4().hex[:8].upper()}"

        word_count = len(raw_text.split())
        processing_time = float(np.random.uniform(280, 850))

        return {
            "patient_id": patient_id,
            "report_type": report_type,
            "source": "synthetic",
            "status": "completed",
            "raw_text": raw_text,
            "cleaned_text": raw_text,
            "word_count": word_count,
            "severity": severity if severity != "normal" else "normal",
            "risk_score": round(risk_score, 4),
            "classification_confidence": round(confidence, 4),
            "ai_summary": self._generate_summary(disease, severity, anatomy),
            "findings_count": 1 if disease.name != "normal" else 0,
            "has_critical_findings": severity == "critical",
            "flagged_for_review": severity in ("severe", "critical"),
            "modality": random.choice(self._modalities.get(report_type, ["Standard"])),
            "body_region": "chest",
            "institution": random.choice(self._institutions),
            "processing_time_ms": round(processing_time, 2),
            "tags": [disease.category, severity, disease.name],
            "metadata": {
                "synthetic": True,
                "disease": disease.name,
                "icd10": disease.icd10,
                "anatomy": anatomy,
                "risk_level": risk_level,
            },
            "created_at": report_date,
            "updated_at": report_date,
        }

    def _generate_summary(self, disease: DiseaseDefinition, severity: str, anatomy: str) -> str:
        if disease.name == "normal":
            return "No acute cardiopulmonary findings identified."
        severity_adj = {"mild": "Mild", "moderate": "Moderate", "severe": "Severe", "critical": "Critical"}
        adj = severity_adj.get(severity, "Moderate")
        finding = random.choice(disease.typical_findings)
        return f"{adj} {disease.normalized.lower()} identified in the {anatomy}. {finding.capitalize()} noted."

    def generate_batch(
        self,
        count: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        disease_distribution: Optional[Dict[str, float]] = None,
    ) -> List[Dict]:
        if start_date is None:
            start_date = datetime.now(timezone.utc) - timedelta(days=365)
        if end_date is None:
            end_date = datetime.now(timezone.utc)

        total_seconds = (end_date - start_date).total_seconds()
        reports = []

        for _ in range(count):
            offset = random.uniform(0, total_seconds)
            report_date = start_date + timedelta(seconds=offset)

            force_disease = None
            if disease_distribution:
                diseases = list(disease_distribution.keys())
                weights = list(disease_distribution.values())
                force_disease = random.choices(diseases, weights=weights, k=1)[0]

            report = self.generate_report(report_date=report_date, force_disease=force_disease)
            reports.append(report)

        reports.sort(key=lambda r: r["created_at"])
        return reports
