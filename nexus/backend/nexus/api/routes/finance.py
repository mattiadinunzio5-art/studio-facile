from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, Query, UploadFile, status

from ...core.errors import ValidationFailedError
from ...services import finance as svc
from ..deps import DB, AppSettings, CurrentUser
from ..schemas_finance import CompareIn, Preset, SeriesCategory, SeriesDetailOut, SeriesImportIn, SeriesOut, SeriesUpdate

router = APIRouter(prefix="/finance", tags=["finance"])


@router.get("/presets", response_model=list[Preset], summary="Serie suggerite (codici reali delle fonti)")
def presets():
    return svc.PRESETS


@router.get("/series", response_model=list[SeriesOut])
def list_series(db: DB, user: CurrentUser, category: SeriesCategory | None = None):
    return [svc.to_out(db, s) for s in svc.list_series(db, user, category)]


@router.post("/series/import", response_model=SeriesDetailOut, status_code=status.HTTP_201_CREATED,
             summary="Importa una serie da World Bank, FRED, OWID o Eurostat")
def import_series(data: SeriesImportIn, db: DB, user: CurrentUser, settings: AppSettings):
    return svc.to_out(db, svc.import_series(db, user, settings, data), detail=True)


@router.post("/series/upload", response_model=SeriesDetailOut, status_code=status.HTTP_201_CREATED,
             summary="Carica una serie da CSV (colonne data, valore)")
async def upload_series(
    db: DB, user: CurrentUser,
    file: Annotated[UploadFile, File()],
    name: Annotated[str, Form(min_length=1, max_length=300)],
    source_label: Annotated[str, Form(min_length=1, max_length=500)],
    unit: Annotated[str, Form(max_length=120)] = "",
    source_url: Annotated[str, Form(max_length=1000)] = "",
    category: Annotated[SeriesCategory, Form()] = "other",
    date_col: Annotated[str | None, Form(max_length=100)] = None,
    value_col: Annotated[str | None, Form(max_length=100)] = None,
):
    raw = await file.read(10 * 1024 * 1024 + 1)
    if len(raw) > 10 * 1024 * 1024:
        raise ValidationFailedError("CSV troppo grande (massimo 10 MB).")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    s, warnings = svc.import_csv(db, user, name=name.strip(), text=text, unit=unit.strip(), source_label=source_label.strip(),
                                 source_url=source_url.strip(), category=category, date_col=date_col or None, value_col=value_col or None)
    out = svc.to_out(db, s, detail=True)
    out.import_warnings = warnings
    return out


@router.get("/series/{series_id}", response_model=SeriesDetailOut)
def get_series(series_id: int, db: DB, user: CurrentUser):
    return svc.to_out(db, svc.get_series(db, user, series_id), detail=True)


@router.patch("/series/{series_id}", response_model=SeriesOut)
def update_series(series_id: int, data: SeriesUpdate, db: DB, user: CurrentUser):
    return svc.to_out(db, svc.update_series(db, user, series_id, data))


@router.post("/series/{series_id}/refresh", response_model=SeriesDetailOut, summary="Riscarica dalla fonte (cache se offline)")
def refresh(series_id: int, db: DB, user: CurrentUser, settings: AppSettings):
    return svc.to_out(db, svc.refresh(db, user, settings, series_id), detail=True)


@router.delete("/series/{series_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_series(series_id: int, db: DB, user: CurrentUser, confirm: bool = False) -> None:
    svc.delete_series(db, user, series_id, confirm)


@router.get("/series/{series_id}/analysis", summary="Rendimenti, volatilità, drawdown, medie mobili, test")
def analysis(
    series_id: int, db: DB, user: CurrentUser,
    ma: list[int] = Query(default=[], description="Finestre delle medie mobili"),
    returns: Literal["simple", "log"] = "simple",
    metrics: Literal["levels", "rates"] | None = None,
):
    if any(w < 2 or w > 1000 for w in ma):
        raise ValidationFailedError("Le finestre delle medie mobili devono essere tra 2 e 1000.")
    return svc.analyze(db, user, series_id, ma, returns, metrics)


@router.post("/compare", summary="Confronto e correlazioni (ricampionamento solo esplicito)")
def compare(data: CompareIn, db: DB, user: CurrentUser):
    return svc.compare(db, user, data)
