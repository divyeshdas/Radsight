from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class DiseaseDefinition:
    name: str
    normalized: str
    icd10: str
    category: str
    anatomy: List[str]
    severity_weights: Dict[str, float]
    prevalence_weight: float
    synonyms: List[str] = field(default_factory=list)
    typical_findings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


DISEASE_REGISTRY: List[DiseaseDefinition] = [
    DiseaseDefinition(
        name="pulmonary edema",
        normalized="Pulmonary Edema",
        icd10="J81.1",
        category="cardiovascular-pulmonary",
        anatomy=["bilateral lungs", "perihilar region", "lung bases"],
        severity_weights={"mild": 0.30, "moderate": 0.45, "severe": 0.20, "critical": 0.05},
        prevalence_weight=0.12,
        synonyms=["pulmonary congestion", "fluid in lungs", "lung edema"],
        typical_findings=[
            "perihilar haziness", "vascular congestion", "Kerley B lines",
            "cephalization of pulmonary vessels", "bilateral interstitial opacities"
        ],
        recommendations=[
            "Correlate with cardiac history", "Echocardiogram recommended",
            "Monitor fluid balance", "BNP levels suggested"
        ],
    ),
    DiseaseDefinition(
        name="pleural effusion",
        normalized="Pleural Effusion",
        icd10="J90",
        category="pleural",
        anatomy=["right pleural space", "left pleural space", "bilateral pleural spaces", "costophrenic angles"],
        severity_weights={"mild": 0.35, "moderate": 0.40, "severe": 0.20, "critical": 0.05},
        prevalence_weight=0.14,
        synonyms=["pleural fluid", "hydrothorax"],
        typical_findings=[
            "blunting of costophrenic angle", "meniscus sign", "homogeneous opacity",
            "fluid tracking", "subpulmonic effusion"
        ],
        recommendations=[
            "Thoracentesis if symptomatic", "CT chest for characterization",
            "Correlate with clinical presentation", "Follow-up imaging in 4-6 weeks"
        ],
    ),
    DiseaseDefinition(
        name="pneumonia",
        normalized="Pneumonia",
        icd10="J18.9",
        category="infectious",
        anatomy=["right lower lobe", "left lower lobe", "right upper lobe", "left upper lobe", "bilateral"],
        severity_weights={"mild": 0.25, "moderate": 0.40, "severe": 0.25, "critical": 0.10},
        prevalence_weight=0.16,
        synonyms=["lobar pneumonia", "bronchopneumonia", "pulmonary consolidation"],
        typical_findings=[
            "lobar consolidation", "air bronchograms", "increased opacity",
            "silhouette sign", "patchy infiltrates", "ground-glass opacity"
        ],
        recommendations=[
            "Antibiotic therapy initiated", "Follow-up chest X-ray in 4-6 weeks",
            "Blood cultures if febrile", "Clinical correlation required"
        ],
    ),
    DiseaseDefinition(
        name="pulmonary nodule",
        normalized="Pulmonary Nodule",
        icd10="R91.1",
        category="neoplastic",
        anatomy=["right upper lobe", "left upper lobe", "right lower lobe", "left lower lobe", "right middle lobe"],
        severity_weights={"mild": 0.40, "moderate": 0.35, "severe": 0.20, "critical": 0.05},
        prevalence_weight=0.08,
        synonyms=["lung nodule", "pulmonary lesion", "lung mass", "solitary nodule"],
        typical_findings=[
            "well-defined nodular opacity", "spiculated margins", "ground-glass nodule",
            "calcified nodule", "subsolid nodule"
        ],
        recommendations=[
            "CT chest for characterization", "PET scan if >8mm",
            "Fleischner Society guidelines apply", "Lung cancer screening follow-up"
        ],
    ),
    DiseaseDefinition(
        name="cardiomegaly",
        normalized="Cardiomegaly",
        icd10="I51.7",
        category="cardiac",
        anatomy=["cardiac silhouette", "left ventricle", "right ventricle"],
        severity_weights={"mild": 0.45, "moderate": 0.35, "severe": 0.15, "critical": 0.05},
        prevalence_weight=0.10,
        synonyms=["enlarged heart", "cardiac enlargement", "increased cardiothoracic ratio"],
        typical_findings=[
            "cardiothoracic ratio >0.5", "enlarged cardiac silhouette",
            "left ventricular enlargement", "globular heart shadow"
        ],
        recommendations=[
            "Echocardiogram recommended", "Cardiology referral",
            "BNP and troponin levels", "EKG correlation"
        ],
    ),
    DiseaseDefinition(
        name="pneumothorax",
        normalized="Pneumothorax",
        icd10="J93.9",
        category="pleural",
        anatomy=["right pleural space", "left pleural space", "apex"],
        severity_weights={"mild": 0.30, "moderate": 0.30, "severe": 0.25, "critical": 0.15},
        prevalence_weight=0.06,
        synonyms=["collapsed lung", "air in pleural space"],
        typical_findings=[
            "visible pleural line", "absent lung markings", "deep sulcus sign",
            "mediastinal shift", "tension pneumothorax"
        ],
        recommendations=[
            "Urgent chest tube placement if tension", "Supplemental oxygen",
            "Serial chest X-rays", "CT chest for extent"
        ],
    ),
    DiseaseDefinition(
        name="atelectasis",
        normalized="Atelectasis",
        icd10="J98.11",
        category="pulmonary",
        anatomy=["right lower lobe", "left lower lobe", "right middle lobe", "bilateral bases"],
        severity_weights={"mild": 0.50, "moderate": 0.35, "severe": 0.12, "critical": 0.03},
        prevalence_weight=0.11,
        synonyms=["subsegmental atelectasis", "plate atelectasis", "discoid atelectasis"],
        typical_findings=[
            "linear opacities", "volume loss", "elevated hemidiaphragm",
            "tracheal deviation", "plate-like densities"
        ],
        recommendations=[
            "Incentive spirometry", "Deep breathing exercises",
            "Chest physiotherapy", "Follow-up if persistent"
        ],
    ),
    DiseaseDefinition(
        name="pulmonary infiltrate",
        normalized="Pulmonary Infiltrate",
        icd10="R91.8",
        category="pulmonary",
        anatomy=["bilateral lungs", "right lung", "left lung", "perihilar"],
        severity_weights={"mild": 0.30, "moderate": 0.40, "severe": 0.20, "critical": 0.10},
        prevalence_weight=0.10,
        synonyms=["bilateral infiltrates", "interstitial infiltrates", "alveolar infiltrates"],
        typical_findings=[
            "bilateral patchy opacities", "interstitial pattern",
            "ground-glass infiltrates", "consolidative changes"
        ],
        recommendations=[
            "BAL if immunocompromised", "CT chest for characterization",
            "Clinical correlation essential", "Infectious workup recommended"
        ],
    ),
    DiseaseDefinition(
        name="rib fracture",
        normalized="Rib Fracture",
        icd10="S22.3",
        category="traumatic",
        anatomy=["right ribs", "left ribs", "posterior ribs", "lateral ribs", "anterior ribs"],
        severity_weights={"mild": 0.35, "moderate": 0.35, "severe": 0.20, "critical": 0.10},
        prevalence_weight=0.06,
        synonyms=["fractured rib", "rib break", "costal fracture"],
        typical_findings=[
            "cortical disruption", "lucent fracture line", "displaced fragments",
            "flail chest", "multiple rib fractures"
        ],
        recommendations=[
            "Pain management", "Pulmonary toilet", "CT for pneumothorax exclusion",
            "Surgical fixation if flail"
        ],
    ),
    DiseaseDefinition(
        name="normal",
        normalized="Normal",
        icd10="Z01.89",
        category="normal",
        anatomy=["chest", "lungs", "mediastinum", "cardiac silhouette"],
        severity_weights={"mild": 0.0, "moderate": 0.0, "severe": 0.0, "critical": 0.0},
        prevalence_weight=0.07,
        synonyms=["no acute findings", "unremarkable", "within normal limits"],
        typical_findings=[
            "clear lung fields", "normal cardiac silhouette",
            "no pleural effusion", "no pneumothorax", "normal mediastinum"
        ],
        recommendations=["Routine follow-up as clinically indicated"],
    ),
]

DISEASE_MAP = {d.name: d for d in DISEASE_REGISTRY}

SEVERITY_TO_RISK = {
    "normal": ("normal", 0.0, 0.15),
    "mild":   ("low",    0.15, 0.35),
    "moderate": ("moderate", 0.35, 0.60),
    "severe": ("high",   0.60, 0.82),
    "critical": ("critical", 0.82, 1.0),
}

REPORT_TEMPLATES = {
    "chest_xray": [
        "PA and lateral chest radiograph obtained. {findings} The cardiac silhouette is {cardiac}. "
        "The mediastinum is {mediastinum}. The osseous structures are {osseous}. {impression}",

        "Frontal and lateral views of the chest are provided. {findings} Cardiac size appears {cardiac}. "
        "No acute bony abnormality. Mediastinal contours are {mediastinum}. {impression}",

        "Two views of the chest performed. {findings} The heart size is {cardiac}. "
        "The mediastinal silhouette is {mediastinum}. {impression}",

        "Portable AP chest radiograph. {findings} Cardiac silhouette is {cardiac}. "
        "Mediastinal width is {mediastinum}. The imaged osseous structures are {osseous}. {impression}",
    ],
    "ct_scan": [
        "CT of the chest performed with contrast. {findings} The heart and great vessels demonstrate {cardiac}. "
        "No significant lymphadenopathy. {impression}",

        "Helical CT chest without and with contrast. {findings} Cardiac chambers appear {cardiac}. "
        "Mediastinal structures are unremarkable. {impression}",
    ],
    "mri": [
        "MRI chest performed without contrast. {findings} Cardiac morphology demonstrates {cardiac}. "
        "No abnormal signal within the mediastinum. {impression}",
    ],
}

NORMAL_PHRASES = [
    "No acute cardiopulmonary process identified.",
    "Lungs are clear without focal consolidation, effusion, or pneumothorax.",
    "No acute intrathoracic process.",
    "Clear lung fields bilaterally.",
]

CARDIAC_DESCRIPTORS = {
    "normal": ["normal in size", "within normal limits", "unremarkable"],
    "mild":   ["mildly enlarged", "borderline enlarged", "mildly increased in size"],
    "moderate": ["moderately enlarged", "increased cardiothoracic ratio", "moderate cardiomegaly"],
    "severe": ["markedly enlarged", "significant cardiomegaly", "severely enlarged"],
}

MEDIASTINUM_DESCRIPTORS = {
    "normal": ["normal", "unremarkable", "within normal limits", "not widened"],
    "abnormal": ["widened", "shifted to the right", "shifted to the left"],
}
