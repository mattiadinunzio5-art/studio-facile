"""NEXUS Daily Briefing.

Generato a richiesta (o da ``scripts/generate_briefing.py``, programmabile con
cron). Ogni voce riporta data e fonte. NEXUS non dispone di un flusso di
notizie: le sezioni che richiederebbero notizie correnti lo dichiarano.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import Settings
from ..core.errors import NexusError
from ..finance import analytics
from ..history import dates
from ..models import Briefing, HistoricalEvent, Project, ResearchRun, Series, SimulationRun, Source, User
from . import activity, finance

SECTIONS = [
    ("global_economy", "Economia globale", {"gdp"}),
    ("monetary_policy", "Politiche monetarie", {"rates"}),
    ("markets", "Mercati finanziari", {"stocks", "indices", "bonds", "commodities", "precious_metals", "fx", "crypto"}),
    ("macro", "Indicatori macroeconomici", {"inflation", "unemployment", "public_debt", "trade_balance"}),
]
STALE_DAYS = {"D": 7, "W": 21, "M": 75, "Q": 200, "A": 550}


def _series_item(db: Session, s: Series, today: date) -> dict:
    out = finance.to_out(db, s)
    item = {"title": s.name, "value": out.last_value, "unit": s.unit, "date": out.last_date, "source": s.source_label,
            "source_updated": s.source_last_updated, "retrieved_at": s.retrieved_at.isoformat() if s.retrieved_at else None,
            "url": f"/financial/series/{s.id}", "flags": []}
    if out.last_date:
        age = (today - datetime.strptime(out.last_date, "%Y-%m-%d").date()).days
        if age > STALE_DAYS[s.frequency]:
            item["flags"].append(f"Ultimo dato del {out.last_date}: la serie potrebbe non essere aggiornata.")
    if s.from_cache:
        item["flags"].append("Ultimo aggiornamento servito dalla cache: fonte non raggiungibile.")
    valid = [o for o in s.observations if o.value is not None]
    if len(valid) >= 2:
        prev = valid[-2]
        item["previous"] = {"value": prev.value, "date": prev.date}
    return item


def generate(db: Session, user: User, settings: Settings, refresh_sources: bool = False, trigger: str = "manual") -> Briefing:
    today = date.today()
    refresh_log = []
    all_series = finance.list_series(db, user)
    if refresh_sources:
        for s in all_series:
            if s.connector == "upload":
                continue
            try:
                finance.refresh(db, user, settings, s.id)
                refresh_log.append({"series": s.name, "status": "aggiornata" if not s.from_cache else "cache (fonte offline)"})
            except NexusError as exc:
                refresh_log.append({"series": s.name, "status": f"errore: {exc.message}"})
    sections = []
    for key, title, cats in SECTIONS:
        items = [_series_item(db, s, today) for s in all_series if s.category in cats]
        sections.append({"key": key, "title": title, "items": items,
                         "empty_reason": None if items else "Nessuna serie importata per questa sezione: nessun dato da riportare."})

    sections.append({"key": "geopolitics", "title": "Eventi geopolitici", "items": [],
                     "empty_reason": "NEXUS non dispone di una fonte di notizie correnti: nessun evento geopolitico in tempo reale. "
                                     "Gli eventi storici dell'archivio sono nella sezione successiva."})

    events = list(db.scalars(select(HistoricalEvent).where(HistoricalEvent.owner_id == user.id)))
    on_this_day = [e for e in events if e.start_month == today.month and e.start_day == today.day]
    related = [e for e in events if {"financial_crisis", "monetary"} & set(e.categories)][:5]
    hist = [{"title": e.title, "date": dates.fmt(e.start_year, e.start_month, e.start_day), "source": "Archivio storico NEXUS", "reliability": e.reliability,
             "reason": "accaduto in questo giorno" if e in on_this_day else "evento monetario/finanziario dell'archivio", "url": f"/history/events/{e.id}"}
            for e in on_this_day + [e for e in related if e not in on_this_day]]
    sections.append({"key": "historical_links", "title": "Collegamenti storici", "items": hist,
                     "empty_reason": None if hist else "Nessun evento dell'archivio collegato alla data o ai temi monetari."})

    topics = []
    for p in db.scalars(select(Project).where(Project.owner_id == user.id, Project.status == "active").limit(10)):
        topics.append({"title": p.title, "kind": "progetto attivo", "date": p.updated_at.date().isoformat(), "source": "Progetti NEXUS", "url": f"/projects?id={p.id}"})
    for r in db.scalars(select(ResearchRun).where(ResearchRun.owner_id == user.id, ResearchRun.status == "awaiting_approval")):
        topics.append({"title": r.question[:150], "kind": "ricerca in attesa di approvazione", "date": r.created_at.date().isoformat(), "source": "Research War Room", "url": f"/war-room/runs/{r.id}"})
    unverified = len(list(db.scalars(select(Source.id).where(Source.owner_id == user.id, Source.verification_status.not_in(("verified_user", "verified_registry"))))))
    if unverified:
        topics.append({"title": f"{unverified} fonti bibliografiche da verificare", "kind": "verifica fonti", "date": today.isoformat(), "source": "Bibliografia", "url": "/bibliography"})
    sections.append({"key": "research_topics", "title": "Argomenti di ricerca", "items": topics, "empty_reason": None if topics else "Nessun argomento aperto."})

    risks = []
    for s in all_series:
        an = analytics.anomalies(analytics.to_pandas([(o.date, o.value) for o in s.observations]))
        recent = [a for a in an if a["date"] >= f"{today.year - 2}-01-01"]
        for a in recent[-2:]:
            risks.append({"title": f"Variazione anomala in «{s.name}»", "detail": f"{a['date']}: variazione {a['change']:.4g} (z robusto {a['z']:.1f})",
                          "date": a["date"], "source": s.source_label, "kind": "dato"})
    for sim in db.scalars(select(SimulationRun).where(SimulationRun.owner_id == user.id).order_by(SimulationRun.id.desc()).limit(3)):
        risks.append({"title": f"Scenario: {sim.title}", "detail": sim.result.get("label", ""), "date": sim.created_at.date().isoformat(),
                      "source": "Economic Laboratory (simulazione, non previsione)", "kind": "scenario", "url": f"/lab/simulations/{sim.id}"})
    sections.append({"key": "risks", "title": "Rischi e scenari da monitorare", "items": risks,
                     "empty_reason": None if risks else "Nessuna anomalia nei dati recenti e nessuno scenario simulato."})

    content = {"date": today.isoformat(), "generated_at": datetime.now().isoformat(timespec="seconds"), "sections": sections,
               "refresh": refresh_log, "notes": ["Valori storici delle fonti indicate, non quotazioni in tempo reale.",
                                                 "Ogni voce riporta la propria data e la propria fonte."]}
    b = Briefing(owner_id=user.id, trigger=trigger, content=content)
    db.add(b)
    db.flush()
    activity.record(db, user=user, actor="user" if trigger == "manual" else "system", action="briefing.generate", entity_type="briefing", entity_id=b.id,
                    summary=f"Generato il Daily Briefing del {today.isoformat()}")
    db.commit()
    db.refresh(b)
    return b


def list_briefings(db: Session, user: User) -> list[Briefing]:
    return list(db.scalars(select(Briefing).where(Briefing.owner_id == user.id).order_by(Briefing.id.desc()).limit(60)))


def get_briefing(db: Session, user: User, bid: int) -> Briefing:
    from ..core.errors import NotFoundError

    b = db.get(Briefing, bid)
    if b is None or b.owner_id != user.id:
        raise NotFoundError("Briefing non trovato.")
    return b
