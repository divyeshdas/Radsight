import re
from typing import Optional


MEDICAL_ABBREVIATIONS = {
    r"\bPA\b": "posteroanterior",
    r"\bAP\b": "anteroposterior",
    r"\bCXR\b": "chest X-ray",
    r"\bCT\b": "computed tomography",
    r"\bMRI\b": "magnetic resonance imaging",
    r"\bBNP\b": "brain natriuretic peptide",
    r"\bBAL\b": "bronchoalveolar lavage",
    r"\bEKG\b": "electrocardiogram",
    r"\bPET\b": "positron emission tomography",
    r"\bLLL\b": "left lower lobe",
    r"\bLUL\b": "left upper lobe",
    r"\bRLL\b": "right lower lobe",
    r"\bRUL\b": "right upper lobe",
    r"\bRML\b": "right middle lobe",
    r"\bSOB\b": "shortness of breath",
    r"\bHTN\b": "hypertension",
    r"\bDM\b": "diabetes mellitus",
    r"\bCAD\b": "coronary artery disease",
    r"\bCHF\b": "congestive heart failure",
    r"\bCOPD\b": "chronic obstructive pulmonary disease",
    r"\bPE\b": "pulmonary embolism",
    r"\bDVT\b": "deep vein thrombosis",
    r"\bICU\b": "intensive care unit",
    r"\bED\b": "emergency department",
    r"\bW\/\b": "with",
    r"\bW\/O\b": "without",
    r"\bS\/P\b": "status post",
    r"\bH\/O\b": "history of",
}

NEGATION_PATTERNS = [
    r"\bno\b\s+\w+",
    r"\bwithout\b\s+\w+",
    r"\babsent\b",
    r"\bnegative\s+for\b",
    r"\brule\s+out\b",
    r"\bunremarkable\b",
    r"\bnot\s+identified\b",
    r"\bnot\s+seen\b",
    r"\bnot\s+detected\b",
]

OCR_NOISE_PATTERNS = [
    (r"[|]{2,}", " "),
    (r"[_]{3,}", " "),
    (r"\s{3,}", " "),
    (r"[^\x00-\x7F]+", " "),
    (r"[\x00-\x08\x0b\x0c\x0e-\x1f]", ""),
    (r"(?<!\w)\.(?!\w)", ". "),
    (r"(\w)([A-Z])", r"\1 \2"),
]


def clean_text(text: str) -> str:
    text = text.strip()

    for pattern, replacement in OCR_NOISE_PATTERNS:
        text = re.sub(pattern, replacement, text)

    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = text.strip()
    return text


def expand_abbreviations(text: str) -> str:
    for pattern, expansion in MEDICAL_ABBREVIATIONS.items():
        text = re.sub(pattern, expansion, text, flags=re.IGNORECASE)
    return text


def normalize_section_headers(text: str) -> str:
    headers = [
        "CLINICAL HISTORY", "INDICATION", "TECHNIQUE", "COMPARISON",
        "FINDINGS", "IMPRESSION", "RECOMMENDATION",
    ]
    for header in headers:
        text = re.sub(
            rf"(?i)\b{header}\b\s*:?",
            f"\n{header}:\n",
            text,
        )
    return text.strip()


def detect_negations(text: str) -> list[dict]:
    negations = []
    for pattern in NEGATION_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            negations.append({"text": match.group(), "start": match.start(), "end": match.end()})
    return negations


def extract_measurements(text: str) -> list[dict]:
    pattern = r"(\d+\.?\d*)\s*(cm|mm|cc|mL|L)"
    measurements = []
    for match in re.finditer(pattern, text, re.IGNORECASE):
        measurements.append({
            "value": float(match.group(1)),
            "unit": match.group(2).lower(),
            "text": match.group(),
            "start": match.start(),
            "end": match.end(),
        })
    return measurements


def normalize_whitespace(text: str) -> str:
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def preprocess_report(raw_text: str, expand_abbrev: bool = False) -> dict:
    cleaned = clean_text(raw_text)
    cleaned = normalize_whitespace(cleaned)
    cleaned = normalize_section_headers(cleaned)

    if expand_abbrev:
        cleaned = expand_abbreviations(cleaned)

    negations = detect_negations(cleaned)
    measurements = extract_measurements(cleaned)

    has_impression = bool(re.search(r"\bIMPRESSION\b", cleaned, re.IGNORECASE))
    has_findings = bool(re.search(r"\bFINDINGS\b", cleaned, re.IGNORECASE))

    sections = _extract_sections(cleaned)

    return {
        "cleaned_text": cleaned,
        "word_count": len(cleaned.split()),
        "char_count": len(cleaned),
        "negation_count": len(negations),
        "negations": negations,
        "measurements": measurements,
        "has_impression_section": has_impression,
        "has_findings_section": has_findings,
        "sections": sections,
    }


def _extract_sections(text: str) -> dict:
    section_patterns = {
        "indication": r"(?i)(?:INDICATION|CLINICAL HISTORY)\s*:\s*(.*?)(?=\n[A-Z]{3,}:|$)",
        "technique": r"(?i)TECHNIQUE\s*:\s*(.*?)(?=\n[A-Z]{3,}:|$)",
        "comparison": r"(?i)COMPARISON\s*:\s*(.*?)(?=\n[A-Z]{3,}:|$)",
        "findings": r"(?i)FINDINGS\s*:\s*(.*?)(?=\nIMPRESSION:|$)",
        "impression": r"(?i)IMPRESSION\s*:\s*(.*?)$",
    }
    sections = {}
    for section, pattern in section_patterns.items():
        match = re.search(pattern, text, re.DOTALL)
        if match:
            sections[section] = match.group(1).strip()
    return sections


def batch_preprocess(texts: list[str], expand_abbrev: bool = False) -> list[dict]:
    return [preprocess_report(t, expand_abbrev=expand_abbrev) for t in texts]
