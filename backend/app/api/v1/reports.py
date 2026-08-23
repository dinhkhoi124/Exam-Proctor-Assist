from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.models.user import User
from app.services.auth_service import get_current_user_from_token, require_manager_or_admin
from app.services.report_service import build_excel_report, build_pdf_report, collect_report_data


router = APIRouter(prefix="/admin/reports", tags=["Admin Reports"])
VALID_GROUPS = {"day", "week", "month", "year"}
VALID_FORMATS = {"xlsx", "pdf"}
VALID_QUESTION_SCOPES = {"user", "manager", "admin", "all"}


def _validate_filters(
    start_date: date,
    end_date: date,
    group_by: str,
    question_scope: str,
) -> None:
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date must be before or equal to end_date")
    if end_date - start_date > timedelta(days=3660):
        raise HTTPException(status_code=400, detail="Report range cannot exceed 10 years")
    if group_by not in VALID_GROUPS:
        raise HTTPException(status_code=400, detail="Invalid group_by")
    if question_scope not in VALID_QUESTION_SCOPES:
        raise HTTPException(status_code=400, detail="Invalid question_scope")


@router.get("/preview")
def preview_report(
    start_date: date,
    end_date: date,
    group_by: str = Query(default="day"),
    question_scope: str = Query(default="user"),
    topic_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    require_manager_or_admin(current_user)
    _validate_filters(start_date, end_date, group_by, question_scope)
    return collect_report_data(
        db,
        start_date,
        end_date,
        group_by,
        topic_id,
        question_scope=question_scope,
    )


@router.get("/export")
def export_report(
    start_date: date,
    end_date: date,
    group_by: str = Query(default="day"),
    question_scope: str = Query(default="user"),
    format: str = Query(default="xlsx"),
    topic_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    require_manager_or_admin(current_user)
    _validate_filters(start_date, end_date, group_by, question_scope)
    if format not in VALID_FORMATS:
        raise HTTPException(status_code=400, detail="Invalid report format")

    data = collect_report_data(
        db,
        start_date,
        end_date,
        group_by,
        topic_id,
        include_details=format == "xlsx",
        question_scope=question_scope,
    )
    filename = (
        f"chatbot-report-{question_scope}-{start_date.isoformat()}-"
        f"{end_date.isoformat()}.{format}"
    )

    if format == "pdf":
        output = build_pdf_report(data)
        media_type = "application/pdf"
    else:
        output = build_excel_report(data)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    return StreamingResponse(
        output,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
