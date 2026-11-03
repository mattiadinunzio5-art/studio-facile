"""Historical Time Machine: cronologia con filtro anti-senno-di-poi.

Regole (modalità rigorosa, ``hindsight=False``):
1. Si mostrano solo eventi iniziati entro l'anno selezionato.
2. Le «conseguenze» descritte in una scheda sono considerate conoscenza
   retrospettiva e vengono nascoste: ciò che era noto all'epoca va registrato
   come informazione datata (``KnowledgeItem``).
3. Delle informazioni datate si mostrano solo quelle note entro l'anno.
4. Gli eventi ancora in corso sono marcati come tali.
5. Degli indicatori economici si mostra l'ultimo valore con data <= anno
   selezionato, avvertendo che i dati possono essere stati rivisti dopo.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..api.schemas_history import KnowledgeOut, TimelineEvent, TimelineIndicator, TimelineOut
from ..history import dates
from ..models import User
from . import history


def timeline(
    db: Session, user: User, *, as_of_year: int | None, hindsight: bool, country: str | None, category: str | None,
    from_year: int | None, to_year: int | None, event_id: int | None = None,
) -> TimelineOut:
    upper = to_year
    if as_of_year is not None and not hindsight:
        upper = min(as_of_year, to_year) if to_year is not None else as_of_year
    all_events = history.list_events(db, user, category=category, country=country, from_year=from_year, to_year=to_year)
    events = [e for e in all_events if upper is None or e.start_year <= upper]
    if event_id is not None:
        events = [e for e in events if e.id == event_id]
    hidden_future = len(all_events) - len([e for e in all_events if upper is None or e.start_year <= upper])

    out = []
    for e in events:
        k_then, k_later = [], []
        for k in e.knowledge:
            (k_then if as_of_year is None or k.known_since_year <= as_of_year else k_later).append(KnowledgeOut.model_validate(k))
        if as_of_year is None:
            status = "not_applicable"
        else:
            end = e.end_year if e.end_year is not None else e.start_year
            status = "ongoing" if end > as_of_year else "concluded"
        strict = as_of_year is not None and not hindsight
        out.append(
            TimelineEvent(
                id=e.id, title=e.title,
                date_label=dates.fmt_range(e.start_year, e.start_month, e.start_day, e.end_year, e.end_month, e.end_day),
                start_year=e.start_year, end_year=e.end_year, status_at_date=status, countries=e.countries,
                categories=e.categories, reliability=e.reliability, description=e.description,
                consequences=None if strict else e.consequences, consequences_hidden=strict and bool(e.consequences),
                known_then=k_then, known_later=[] if strict else k_later, hidden_later_count=len(k_later) if strict else 0,
                is_demo=e.is_demo,
            )
        )

    indicators = _indicators_as_of(db, user, as_of_year) if as_of_year is not None else []
    notes = []
    if as_of_year is not None and not hindsight:
        notes.append(f"Vista rigorosa al {dates.fmt(as_of_year)}: nascosti eventi successivi, conseguenze retrospettive e informazioni emerse dopo.")
    if as_of_year is not None and hindsight:
        notes.append("Senno di poi attivo: sono incluse informazioni non disponibili all'epoca, evidenziate come tali.")
    if indicators:
        notes.append("Gli indicatori mostrano i valori attuali delle serie fino alla data scelta: possono differire dai dati pubblicati all'epoca (revisioni).")
    return TimelineOut(
        as_of_year=as_of_year, hindsight=hindsight,
        filters={"country": country, "category": category, "from_year": from_year, "to_year": to_year},
        events=out, indicators=indicators, hidden_future_events=hidden_future if not hindsight else 0, notes=notes,
    )


def _indicators_as_of(db: Session, user: User, year: int) -> list[TimelineIndicator]:
    try:
        from ..models import Observation, Series
    except ImportError:  # Fase 4 non ancora installata
        return []
    result = []
    for s in db.scalars(select(Series).where(Series.owner_id == user.id)):
        obs = db.scalar(
            select(Observation)
            .where(Observation.series_id == s.id, Observation.date <= f"{year}-12-31", Observation.value.is_not(None))
            .order_by(Observation.date.desc())
            .limit(1)
        )
        if obs is not None:
            result.append(
                TimelineIndicator(
                    series_id=s.id, name=s.name, unit=s.unit, source=s.source_label, last_date=obs.date, last_value=obs.value,
                    caveat="Valore della versione attuale della serie (possibili revisioni successive).",
                )
            )
    return result
