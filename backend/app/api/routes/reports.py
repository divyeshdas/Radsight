import time
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, Query
from pydantic import BaseModel
from app.models.report import RadiologyReport, ReportType, ReportStatus, SeverityLevel
from app.services.report_service import (
    create_report, get_report, list_reports, delete_report, get_report_stats
)
from app.api.dependencies.auth import CurrentUser, RadiologistOrAdmin
from app.core.config import get_settings
from app.core.exceptions import ProcessingError
from app.core.logging import get_logger

router = APIRouter(prefix="/reports", tags=["reports"])
settings = get_settings()
logger = get_logger(__name__)


class PaginatedReports(BaseModel):
    items: list[RadiologyReport]
    total: int
    page: int
    page_size: int
    pages: int


@router.post("/upload", response_model=RadiologyReport, status_code=201, response_model_by_alias=False)
async def upload_report(
    current_user: CurrentUser,
    file: UploadFile = File(...),
    patient_id: str = Form(...),
    report_type: ReportType = Form(ReportType.chest_xray),
    institution: Optional[str] = Form(None),
):
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename else ""
    if ext not in settings.allowed_extensions_list:
        raise ProcessingError(f"File type '{ext}' not supported", {"allowed": settings.allowed_extensions_list})

    content = await file.read()
    if len(content) > settings.max_upload_size_mb * 1024 * 1024:
        raise ProcessingError(f"File exceeds {settings.max_upload_size_mb}MB limit")

    from app.services.scan_processor import process_upload
    analysis = process_upload(content, ext, file.filename or "")

    report = await create_report(
        patient_id=patient_id,
        raw_text=analysis.pop("raw_text", ""),
        report_type=report_type,
        source="upload",
        institution=institution,
        radiologist_id=str(current_user.id),
        metadata={"original_filename": file.filename, "file_size_bytes": len(content)},
        analysis=analysis,
    )
    return report


@router.post("/ingest", response_model=RadiologyReport, status_code=201)
async def ingest_text_report(
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    patient_id: str,
    raw_text: str,
    report_type: ReportType = ReportType.chest_xray,
    institution: Optional[str] = None,
):
    report = await create_report(
        patient_id=patient_id,
        raw_text=raw_text,
        report_type=report_type,
        source="api",
        institution=institution,
        radiologist_id=str(current_user.id),
    )
    background_tasks.add_task(_trigger_nlp_processing, str(report.id))
    return report


@router.get("/")
async def list_reports_endpoint(
    current_user: CurrentUser,
    patient_id: Optional[str] = Query(None),
    severity: Optional[SeverityLevel] = Query(None),
    status: Optional[ReportStatus] = Query(None),
    report_type: Optional[ReportType] = Query(None),
    flagged: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    from app.db.mongodb import get_database
    db = get_database()
    collection = db["reports"]

    query: dict = {}
    if patient_id:
        query["patient_id"] = {"$regex": patient_id.strip(), "$options": "i"}
    if severity:
        query["severity"] = str(severity)
    if status:
        query["status"] = str(status)
    if report_type:
        query["report_type"] = str(report_type)
    if flagged is not None:
        query["flagged_for_review"] = flagged

    total = await collection.count_documents(query)
    skip = (page - 1) * page_size
    projection = {"raw_text": 0, "cleaned_text": 0}
    cursor = collection.find(query, projection).sort("created_at", -1).skip(skip).limit(page_size)
    docs = await cursor.to_list(length=page_size)

    items = []
    for d in docs:
        created = d.get("created_at")
        updated = d.get("updated_at")
        items.append({
            "id": str(d["_id"]),
            "patient_id": d.get("patient_id", ""),
            "report_type": d.get("report_type", "chest_xray"),
            "status": d.get("status", "completed"),
            "severity": d.get("severity"),
            "risk_score": d.get("risk_score"),
            "classification_confidence": d.get("classification_confidence"),
            "ai_summary": d.get("ai_summary"),
            "findings_count": d.get("findings_count", 0),
            "has_critical_findings": bool(d.get("has_critical_findings", False)),
            "flagged_for_review": bool(d.get("flagged_for_review", False)),
            "processing_time_ms": d.get("processing_time_ms"),
            "tags": d.get("tags", []),
            "institution": d.get("institution"),
            "created_at": created.isoformat() if created else None,
            "updated_at": updated.isoformat() if updated else None,
        })

    pages = -(-total // page_size) if total else 0
    return {"items": items, "total": total, "page": page, "page_size": page_size, "pages": pages}


@router.get("/stats")
async def report_stats(current_user: CurrentUser):
    return await get_report_stats()


@router.get("/{report_id}", response_model=RadiologyReport)
async def get_report_endpoint(report_id: str, current_user: CurrentUser):
    return await get_report(report_id)


@router.delete("/{report_id}", status_code=204)
async def delete_report_endpoint(report_id: str, current_user: RadiologistOrAdmin):
    await delete_report(report_id)


async def _trigger_nlp_processing(report_id: str) -> None:
    import httpx
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            await client.post(f"http://ai_services:8001/nlp/process/{report_id}")
    except Exception as e:
        logger.error("NLP trigger failed", report_id=report_id, error=str(e))


async def _trigger_ocr_processing(report_id: str, content: bytes, ext: str) -> None:
    import httpx
    try:
        async with httpx.AsyncClient(timeout=180) as client:
            await client.post(
                f"http://ai_services:8001/ocr/process/{report_id}",
                content=content,
                headers={"Content-Type": f"application/{ext}"},
            )
    except Exception as e:
        logger.error("OCR trigger failed", report_id=report_id, error=str(e))
