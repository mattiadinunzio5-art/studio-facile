from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, Query, UploadFile, status
from fastapi.responses import FileResponse

from ...services import documents as svc
from ..deps import DB, AppSettings, CurrentUser
from ..schemas_research import ChunkOut, DocumentOut, DocumentUpdate, GutenbergImportIn

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentOut])
def list_documents(db: DB, user: CurrentUser, project_id: int | None = None,
                   category: Literal["source_material", "user_work", "dataset"] | None = None):
    return svc.list_documents(db, user, project_id, category)


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED,
             summary="Importa un documento (PDF, DOCX, CSV, XLSX, TXT, MD)")
async def upload(
    db: DB,
    user: CurrentUser,
    settings: AppSettings,
    file: Annotated[UploadFile, File()],
    title: Annotated[str | None, Form(max_length=300)] = None,
    category: Annotated[Literal["source_material", "user_work", "dataset"], Form()] = "source_material",
    project_id: Annotated[int | None, Form()] = None,
    author: Annotated[str, Form(max_length=300)] = "",
):
    limit = settings.max_upload_mb * 1024 * 1024
    data = await file.read(limit + 1)
    return svc.import_bytes(
        db, user, settings, filename=file.filename or "documento", data=data, title=(title or "").strip() or None,
        category=category, project_id=project_id, author=author.strip(),
    )


@router.post("/gutenberg", response_model=DocumentOut, status_code=status.HTTP_201_CREATED,
             summary="Importa un singolo testo da Project Gutenberg (su richiesta dell'utente)")
def import_gutenberg(data: GutenbergImportIn, db: DB, user: CurrentUser, settings: AppSettings):
    return svc.import_gutenberg(db, user, settings, data.ebook_id, data.title, data.author, data.project_id)


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: int, db: DB, user: CurrentUser):
    return svc.get_document(db, user, document_id)


@router.patch("/{document_id}", response_model=DocumentOut)
def update_document(document_id: int, data: DocumentUpdate, db: DB, user: CurrentUser):
    return svc.update_document(db, user, document_id, data)


@router.get("/{document_id}/chunks", response_model=list[ChunkOut])
def get_chunks(document_id: int, db: DB, user: CurrentUser, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200)):
    return svc.get_chunks(db, user, document_id, offset, limit)


@router.get("/{document_id}/file", summary="Scarica il file originale")
def download(document_id: int, db: DB, user: CurrentUser, settings: AppSettings):
    d = svc.get_document(db, user, document_id)
    return FileResponse(svc.file_path(settings, d), filename=d.filename, content_disposition_type="attachment")


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: int, db: DB, user: CurrentUser, settings: AppSettings, confirm: bool = False) -> None:
    svc.delete_document(db, user, settings, document_id, confirm)
