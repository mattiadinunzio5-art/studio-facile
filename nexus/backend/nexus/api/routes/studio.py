from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Query, Response, status

from ...services import briefing as briefing_svc
from ...services import studio as svc
from ..deps import DB, AppSettings, CurrentUser
from ..schemas_studio import (
    BriefingIn, BriefingOut, ChapterIn, NoteIn, NoteOut, ReportCheck, ReportCreate, ReportOut, ReportSummary, ReportUpdate, SectionIn,
)

router = APIRouter(tags=["research-studio"])


@router.get("/reports", response_model=list[ReportSummary])
def list_reports(db: DB, user: CurrentUser, project_id: int | None = None):
    return svc.list_reports(db, user, project_id)


@router.post("/reports", response_model=ReportOut, status_code=status.HTTP_201_CREATED, summary="Nuovo rapporto con le 10 sezioni standard")
def create_report(data: ReportCreate, db: DB, user: CurrentUser):
    return svc.create_report(db, user, data)


@router.post("/reports/from-run/{run_id}", response_model=ReportOut, status_code=status.HTTP_201_CREATED,
             summary="Bozza di rapporto da una ricerca approvata della War Room")
def report_from_run(run_id: int, db: DB, user: CurrentUser):
    return svc.from_research_run(db, user, run_id)


@router.get("/reports/{report_id}", response_model=ReportOut)
def get_report(report_id: int, db: DB, user: CurrentUser):
    return svc.get_report(db, user, report_id)


@router.patch("/reports/{report_id}", response_model=ReportOut)
def update_report(report_id: int, data: ReportUpdate, db: DB, user: CurrentUser):
    return svc.update_report(db, user, report_id, data)


@router.put("/reports/{report_id}/sections/{section_id}", response_model=ReportOut)
def update_section(report_id: int, section_id: int, data: SectionIn, db: DB, user: CurrentUser):
    return svc.update_section(db, user, report_id, section_id, data)


@router.post("/reports/{report_id}/chapters", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def add_chapter(report_id: int, data: ChapterIn, db: DB, user: CurrentUser):
    return svc.add_chapter(db, user, report_id, data)


@router.post("/reports/{report_id}/chapters/{section_id}/move", response_model=ReportOut)
def move_chapter(report_id: int, section_id: int, db: DB, user: CurrentUser, direction: int = Query(1, ge=-1, le=1)):
    return svc.move_chapter(db, user, report_id, section_id, direction)


@router.delete("/reports/{report_id}/chapters/{section_id}", response_model=ReportOut)
def delete_chapter(report_id: int, section_id: int, db: DB, user: CurrentUser):
    return svc.delete_chapter(db, user, report_id, section_id)


@router.get("/reports/{report_id}/check", response_model=ReportCheck, summary="Verifica sezioni, citazioni e fonti")
def check_report(report_id: int, db: DB, user: CurrentUser):
    return svc.check(db, user, report_id)


@router.post("/reports/{report_id}/status", response_model=ReportOut, summary="Approva il rapporto o riportalo in bozza")
def set_status(report_id: int, db: DB, user: CurrentUser, value: Literal["approved", "draft"]):
    return svc.set_status(db, user, report_id, value)


@router.get("/reports/{report_id}/export/{fmt}", summary="Esporta in PDF o DOCX")
def export_report(report_id: int, fmt: Literal["pdf", "docx"], db: DB, user: CurrentUser):
    data, title = svc.export_report(db, user, report_id, fmt)
    media = "application/pdf" if fmt == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    name = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)[:80].strip() or "rapporto"
    return Response(data, media_type=media, headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}.{fmt}"})


@router.delete("/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(report_id: int, db: DB, user: CurrentUser, confirm: bool = False) -> None:
    svc.delete_report(db, user, report_id, confirm)


@router.get("/notes", response_model=list[NoteOut])
def list_notes(db: DB, user: CurrentUser, project_id: int | None = None):
    return svc.list_notes(db, user, project_id)


@router.post("/notes", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
def create_note(data: NoteIn, db: DB, user: CurrentUser):
    return svc.create_note(db, user, data)


@router.put("/notes/{note_id}", response_model=NoteOut)
def update_note(note_id: int, data: NoteIn, db: DB, user: CurrentUser):
    return svc.update_note(db, user, note_id, data)


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: int, db: DB, user: CurrentUser, confirm: bool = False) -> None:
    svc.delete_note(db, user, note_id, confirm)


@router.post("/briefings", response_model=BriefingOut, status_code=status.HTTP_201_CREATED, summary="Genera il Daily Briefing")
def generate_briefing(data: BriefingIn, db: DB, user: CurrentUser, settings: AppSettings):
    return briefing_svc.generate(db, user, settings, data.refresh_sources)


@router.get("/briefings", response_model=list[BriefingOut])
def list_briefings(db: DB, user: CurrentUser):
    return briefing_svc.list_briefings(db, user)


@router.get("/briefings/{briefing_id}", response_model=BriefingOut)
def get_briefing(briefing_id: int, db: DB, user: CurrentUser):
    return briefing_svc.get_briefing(db, user, briefing_id)
