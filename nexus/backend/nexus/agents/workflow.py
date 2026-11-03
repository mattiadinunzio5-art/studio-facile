"""Research War Room: flusso multi-agente supervisionato.

Domanda → Pianificazione → Ricerca → Analisi (Historian, Economist, Quant) →
Controanalisi (Skeptic) → Sintesi (Synthesizer) → Approvazione dell'utente.

Due modalità, sempre dichiarate:
- **ai**: gli agenti sono eseguiti da un modello configurato dall'utente; ogni
  risposta passa dai controlli di ``guard`` (nessuna ipotesi promossa a fatto).
- **local**: senza modello AI. Pianificazione, ricerca, quant (calcoli),
  storico (estrazione dall'archivio), controanalisi (regole) e sintesi
  (dossier) sono eseguiti dal motore locale; l'Economist, che richiede
  ragionamento generativo, è registrato come **non eseguito**.

Gli strumenti (ricerca nei documenti, eventi, serie) sono sempre eseguiti
localmente sui dati reali dell'utente: il modello AI non ha accesso diretto a
database, rete o file.
"""

from __future__ import annotations

import json
import time
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import Settings
from ..database.base import utcnow
from ..finance import analytics
from ..models import Entity, HistoricalEvent, ResearchRun, Series, Source, User
from ..models.graph import RELATION_TYPES
from ..research.answer import extract_claims
from ..research.safety import wrap_untrusted
from ..research.text import terms
from . import guard, llm, prompts


class StepLimitExceeded(Exception):
    pass


class Runner:
    def __init__(self, db: Session, run: ResearchRun, user: User, settings: Settings, client: llm.LLMClient | None):
        self.db, self.run, self.user, self.settings, self.client = db, run, user, settings, client
        self.ordinal = 0

    # --- registrazione dei passi ---------------------------------------------------------

    def step(self, agent: str, *, status: str, executor: str, summary: str, output: dict | None = None,
             issues: list[str] | None = None, error: str | None = None, res: llm.LLMResult | None = None, t0: float | None = None):
        from ..models import AgentStep

        self.ordinal += 1
        if self.ordinal > self.settings.max_agent_steps:
            raise StepLimitExceeded(f"Superato il limite di {self.settings.max_agent_steps} passi automatici.")
        self.run.steps.append(AgentStep(
            ordinal=self.ordinal, agent=agent, status=status, executor=executor, summary=summary[:2000], output=output or {},
            issues=(issues or []) + (res.notes if res else []), error=error,
            provider=res.provider if res else ("nexus-local" if executor == "local" else ""), model=res.model if res else "",
            duration_ms=res.duration_ms if res else int((time.perf_counter() - (t0 or time.perf_counter())) * 1000),
            input_tokens=res.input_tokens if res else None, output_tokens=res.output_tokens if res else None,
        ))
        self.db.commit()

    def ai(self, role: str, user_prompt: str, max_tokens: int = 4000) -> tuple[dict, llm.LLMResult]:
        res = self.client.complete(prompts.ROLES[role], user_prompt, max_tokens)  # type: ignore[union-attr]
        return guard.parse_json(res.text), res

    # --- fasi --------------------------------------------------------------------

    def plan(self) -> dict:
        q = self.run.question
        local_terms = terms(q)
        local = {"sub_questions": [], "search_queries": [q, " ".join(local_terms[:4])] if local_terms else [q],
                 "terms": local_terms[:12], "method": "estrazione dei termini (locale)"}
        if self.client:
            t0 = time.perf_counter()
            try:
                data, res = self.ai("planner", f"Domanda di ricerca:\n{q}")
                queries = [str(x)[:200] for x in data.get("search_queries", []) if str(x).strip()][:6]
                plan = {**local, "sub_questions": [str(x)[:300] for x in data.get("sub_questions", [])][:5],
                        "search_queries": list(dict.fromkeys([q, *queries])), "method": "pianificazione AI"}
                self.step("planner", status="executed", executor="ai", summary=f"{len(plan['sub_questions'])} sotto-domande, {len(plan['search_queries'])} query", output=plan, res=res)
                return plan
            except (llm.ProviderError, guard.ParseError) as exc:
                self.step("planner", status="failed", executor="ai", summary="Pianificazione AI non riuscita: uso la pianificazione locale.", error=str(exc), t0=t0)
        self.step("planner", status="executed", executor="local", summary=f"Query: {', '.join(local['search_queries'])}", output=local)
        return local

    def research(self, plan: dict) -> tuple[list[dict], list[str]]:
        from ..services import research

        t0 = time.perf_counter()
        evidence: list[dict] = []
        seen_chunks: set[int] = set()
        for qq in plan["search_queries"]:
            passages, _ = research.retrieve(self.db, self.user, self.settings, qq, "hybrid", 6, self.run.options.get("document_ids"))
            for p in passages:
                if p.chunk_id not in seen_chunks and len(seen_chunks) < 12:
                    seen_chunks.add(p.chunk_id)
                    evidence.append({"kind": "passage", "label": f"{p.document_title}, {p.locator}".strip(", "), "text": p.text[:1500],
                                     "ref": {"chunk_id": p.chunk_id, "document_id": p.document_id}, "source": p.source_label,
                                     "injection_flag": p.injection_flag})
        # Eventi: punteggio = numero di termini della domanda presenti in titolo/descrizione.
        tset = set(plan.get("terms", []))
        scored = []
        for e in self.db.scalars(select(HistoricalEvent).where(HistoricalEvent.owner_id == self.user.id)):
            hay = set(terms(" ".join([e.title, e.description, e.causes, e.economic_implications, " ".join(e.countries)])))
            s = len(tset & hay)
            if s:
                scored.append((s, e))
        for _, e in sorted(scored, key=lambda x: -x[0])[:8]:
            n_src = len(e.source_links)
            verified = sum(1 for link in e.source_links if (src := self.db.get(Source, link.source_id)) and src.verification_status in ("verified_user", "verified_registry"))
            text = f"{e.title} ({e.start_year}{'–' + str(e.end_year) if e.end_year and e.end_year != e.start_year else ''}). {e.description} Cause: {e.causes} Implicazioni economiche: {e.economic_implications}"
            evidence.append({"kind": "event", "label": f"Evento: {e.title}", "text": text[:1500], "ref": {"event_id": e.id},
                             "source": f"Archivio storico NEXUS — attendibilità {e.reliability}, {n_src} fonti ({verified} verificate)",
                             "reliability": e.reliability, "verified_sources": verified, "injection_flag": False})
        # Serie: selezionate esplicitamente o con nome pertinente; statistiche calcolate localmente.
        ids = self.run.options.get("series_ids") or []
        candidates = list(self.db.scalars(select(Series).where(Series.owner_id == self.user.id)))
        chosen = [s for s in candidates if s.id in ids]
        if not ids:
            chosen = [s for s in candidates if tset & set(terms(s.name + " " + s.category))][:4]
        for s in chosen:
            evidence.append(self._series_evidence(s))
        for i, ev in enumerate(evidence, start=1):
            ev["id"] = f"E{i}"
        counts = Counter(e["kind"] for e in evidence)
        issues = [] if evidence else ["Nessuna evidenza trovata nell'archivio."]
        self.step("researcher", status="executed", executor="local", t0=t0,
                  summary=f"Evidenze raccolte: {counts.get('passage', 0)} passaggi, {counts.get('event', 0)} eventi, {counts.get('series', 0)} serie",
                  output={"counts": dict(counts)}, issues=issues)
        return evidence, issues

    def _series_evidence(self, s: Series) -> dict:
        inp = analytics.SeriesInput(s.id, s.name, s.frequency, s.unit, [(o.date, o.value) for o in s.observations])
        try:
            a = analytics.analyze(inp, [], level_metrics=s.category in {"stocks", "indices", "commodities", "precious_metals", "fx", "crypto", "gdp"})
            sm = a["summary"]
            parts = [f"{s.name} [{s.unit}, freq. {s.frequency}]: periodo {sm['first_date']} → {sm['last_date']}, {sm['valid']} valori, {sm['missing']} mancanti",
                     f"primo valore {sm['first_value']}, ultimo {sm['last_value']}, min {sm['min']}, max {sm['max']}, media {round(sm['mean'], 4)}"]
            if "returns" in a:
                r = a["returns"]
                parts.append(f"variazione totale {r['total_change']}, CAGR {r['cagr']}, volatilità annualizzata {r['volatility_annualized']}")
                if a.get("drawdown"):
                    parts.append(f"max drawdown {a['drawdown']['max_drawdown']} ({a['drawdown']['peak_date']} → {a['drawdown']['trough_date']})")
            else:
                parts.append(f"variazione media per periodo {a['changes']['mean']}")
            adf = a["timeseries"].get("adf")
            if adf and "p_value" in adf:
                parts.append(f"test ADF p={round(adf['p_value'], 4)}")
            stats = {"summary": sm, "returns": a.get("returns"), "changes": a.get("changes"), "drawdown": a.get("drawdown")}
        except analytics.AnalysisError as exc:
            parts, stats = [f"{s.name}: statistiche non calcolabili ({exc})"], {}
        return {"kind": "series", "label": f"Serie: {s.name}", "text": "; ".join(parts), "ref": {"series_id": s.id},
                "source": s.source_label + (f" (aggiornamento fonte {s.source_last_updated})" if s.source_last_updated else ""),
                "stats": stats, "missing": s.missing_count, "injection_flag": False}

    def evidence_block(self, evidence: list[dict], kinds: set[str] | None = None) -> str:
        return "\n".join(wrap_untrusted(e["id"], f"{e['label']} — {e['source']}", e["text"]) for e in evidence if not kinds or e["kind"] in kinds)

    def analysis(self, evidence: list[dict]) -> dict[str, list[dict]]:
        ev_by_id = {e["id"]: e for e in evidence}
        results: dict[str, list[dict]] = {}
        q = self.run.question
        for role, kinds in (("historian", {"passage", "event"}), ("economist", {"passage", "series", "event"}), ("quant", {"series"})):
            t0 = time.perf_counter()
            relevant = [e for e in evidence if e["kind"] in kinds]
            if self.client:
                if not relevant:
                    self.step(role, status="skipped", executor="none", summary="Nessuna evidenza pertinente per questo agente: non eseguito.")
                    results[role] = []
                    continue
                try:
                    data, res = self.ai(role, f"Domanda: {q}\n\nEvidenze:\n{self.evidence_block(relevant)}")
                    claims, issues = guard.validate_claims(data.get("claims"), {e["id"]: e for e in relevant})
                    results[role] = claims
                    self.step(role, status="executed", executor="ai", summary=str(data.get("notes", ""))[:1000] or f"{len(claims)} affermazioni",
                              output={"claims": claims}, issues=issues, res=res)
                except (llm.ProviderError, guard.ParseError) as exc:
                    results[role] = []
                    self.step(role, status="failed", executor="ai", summary="Agente non riuscito.", error=str(exc), t0=t0)
                continue
            # Modalità locale
            if role == "historian":
                claims = self._local_historian(q, [e for e in relevant])
                self.step(role, status="executed", executor="local", t0=t0, output={"claims": claims},
                          summary=f"Estrazione dall'archivio (senza AI): {len(claims)} affermazioni con evidenza.")
            elif role == "quant":
                claims = self._local_quant(relevant)
                self.step(role, status="executed", executor="local", t0=t0, output={"claims": claims},
                          summary=f"Statistiche calcolate localmente su {len(relevant)} serie." if relevant else "Nessuna serie pertinente: nessun calcolo.")
            else:
                claims = []
                self.step(role, status="skipped", executor="none",
                          summary="Non eseguito: l'analisi economica interpretativa richiede un provider AI configurato.")
            results[role] = claims
        return results

    def _local_historian(self, q: str, evidence: list[dict]) -> list[dict]:
        from ..research.answer import Passage

        passages = [Passage(e["ref"]["chunk_id"], e["ref"]["document_id"], e["label"], None, "", e["text"], 0, e["injection_flag"], e["source"])
                    for e in evidence if e["kind"] == "passage"]
        claims = []
        id_of_chunk = {e["ref"].get("chunk_id"): e["id"] for e in evidence if e["kind"] == "passage"}
        for c in extract_claims(q, passages, max_claims=5):
            if c["type"] == "missing":
                continue
            c["evidence"] = [id_of_chunk[x] for x in c["evidence"]]
            claims.append(c)
        for e in evidence:
            if e["kind"] != "event":
                continue
            verified = e.get("verified_sources", 0) > 0 and e.get("reliability") in ("established", "probable")
            claims.append({"type": "documented_fact" if verified else "interpretation", "text": e["text"][:400], "evidence": [e["id"]],
                           "support": "partial", "coverage": 0.0,
                           "note": "Scheda d'archivio con fonti verificate." if verified else
                           "Scheda d'archivio senza fonti verificate o con attendibilità bassa: non trattata come fatto documentato."})
        return claims

    def _local_quant(self, evidence: list[dict]) -> list[dict]:
        claims = []
        for e in evidence:
            sm = (e.get("stats") or {}).get("summary")
            if not sm:
                claims.append({"type": "missing", "text": e["text"], "evidence": [], "support": "none", "coverage": 0.0, "note": ""})
                continue
            claims.append({"type": "documented_fact", "text": f"{e['label']}: ultimo valore pubblicato {sm['last_value']} ({sm['last_date']}).",
                           "evidence": [e["id"]], "support": "strong", "coverage": 1.0, "note": f"Fonte: {e['source']}"})
            claims.append({"type": "estimate", "text": e["text"], "evidence": [e["id"]], "support": "strong", "coverage": 1.0,
                           "note": "Valori calcolati deterministicamente da NEXUS sui dati della fonte (nessuna previsione)."})
        return claims

    def skeptic(self, evidence: list[dict], analyses: dict[str, list[dict]]) -> tuple[list[dict], list[str]]:
        t0 = time.perf_counter()
        checks = self._rule_checks(evidence, analyses)
        if self.client and any(analyses.values()):
            try:
                claims_txt = json.dumps({k: v for k, v in analyses.items()}, ensure_ascii=False)[:20000]
                data, res = self.ai("skeptic", f"Domanda: {self.run.question}\n\nAffermazioni degli agenti (JSON):\n{claims_txt}\n\n"
                                                f"Controlli automatici già rilevati: {checks}\n\nEvidenze:\n{self.evidence_block(evidence)}")
                claims, issues = guard.validate_claims(data.get("claims"), {e["id"]: e for e in evidence})
                self.step("skeptic", status="executed", executor="ai", summary=str(data.get("notes", ""))[:1000] or f"{len(claims)} obiezioni",
                          output={"claims": claims, "rule_checks": checks}, issues=issues, res=res)
                return claims, checks
            except (llm.ProviderError, guard.ParseError) as exc:
                self.step("skeptic", status="failed", executor="ai", summary="Controanalisi AI non riuscita; restano i controlli automatici.",
                          output={"rule_checks": checks}, error=str(exc), t0=t0)
                return [], checks
        self.step("skeptic", status="executed", executor="local", t0=t0, output={"rule_checks": checks},
                  summary=f"Controanalisi a regole (senza AI): {len(checks)} rilievi.")
        return [], checks

    def _rule_checks(self, evidence: list[dict], analyses: dict[str, list[dict]]) -> list[str]:
        out = []
        if not evidence:
            out.append("Nessuna evidenza: qualsiasi conclusione sarebbe priva di supporto.")
        docs = {e["ref"].get("document_id") for e in evidence if e["kind"] == "passage"}
        if len(docs) == 1 and sum(1 for e in evidence if e["kind"] == "passage") > 1:
            out.append("Tutti i passaggi provengono da un solo documento: manca un confronto tra fonti indipendenti.")
        if any("senza scheda bibliografica" in e["source"] for e in evidence if e["kind"] == "passage"):
            out.append("Alcuni documenti non hanno una scheda bibliografica: le citazioni non sono pienamente verificabili.")
        flagged = [e["id"] for e in evidence if e.get("injection_flag")]
        if flagged:
            out.append(f"Evidenze {', '.join(flagged)} contengono frasi simili a istruzioni per un'AI: trattate solo come dato.")
        weak_events = [e["label"] for e in evidence if e["kind"] == "event" and (e.get("reliability") in ("disputed", "unverified") or not e.get("verified_sources"))]
        if weak_events:
            out.append(f"{len(weak_events)} eventi con attendibilità bassa o senza fonti verificate.")
        miss = [e["label"] for e in evidence if e["kind"] == "series" and e.get("missing")]
        if miss:
            out.append(f"Serie con dati mancanti: {', '.join(miss)}.")
        if any(e["kind"] == "series" for e in evidence) and any(w in self.run.question.lower() for w in ("caus", "perché", "effetto", "provoc", "why", "cause")):
            out.append("La domanda è causale: andamenti e correlazioni tra serie non dimostrano causalità.")
        types = Counter(c["type"] for cl in analyses.values() for c in cl)
        if types and types.get("documented_fact", 0) == 0:
            out.append("Nessuna affermazione è supportata come fatto documentato.")
        return out

    def synthesize(self, evidence: list[dict], analyses: dict[str, list[dict]], skeptic_claims: list[dict], checks: list[str]) -> dict:
        t0 = time.perf_counter()
        ev_by_id = {e["id"]: e for e in evidence}
        if self.client and (any(analyses.values()) or skeptic_claims):
            entities = [e.name for e in self.db.scalars(select(Entity).where(Entity.owner_id == self.user.id).limit(200))]
            try:
                payload = json.dumps({"analisi": analyses, "controanalisi": skeptic_claims, "controlli": checks}, ensure_ascii=False)[:30000]
                data, res = self.ai("synthesizer", f"Domanda: {self.run.question}\n\nRisultati (JSON):\n{payload}\n\n"
                                                    f"Entità del Knowledge Graph: {json.dumps(entities, ensure_ascii=False)}\n\n"
                                                    f"Evidenze:\n{self.evidence_block(evidence)}", max_tokens=8000)
                claims, issues = guard.validate_claims(data.get("claims"), ev_by_id)
                proposals, p_issues = self._validate_proposals(data.get("proposed_relations"), ev_by_id)
                result = {"abstract": str(data.get("notes", ""))[:4000], "claims": claims, "proposed_relations": proposals,
                          "limitations": checks, "method": "Sintesi generata da modello AI e verificata dai controlli NEXUS."}
                self.step("synthesizer", status="executed", executor="ai", summary=f"Sintesi: {len(claims)} affermazioni, {len(proposals)} relazioni proposte",
                          output=result, issues=issues + p_issues, res=res)
                return result
            except (llm.ProviderError, guard.ParseError) as exc:
                self.step("synthesizer", status="failed", executor="ai", summary="Sintesi AI non riuscita: compilo il dossier locale.", error=str(exc), t0=t0)
        seen, claims = set(), []
        for c in [c for cl in analyses.values() for c in cl] + skeptic_claims:
            key = c["text"][:150]
            if key not in seen:
                seen.add(key)
                claims.append(c)
        result = {"abstract": "", "claims": claims, "proposed_relations": [], "limitations": checks,
                  "method": "Dossier compilato localmente (nessun testo generato): affermazioni estratte e calcoli, con i rilievi della controanalisi."}
        self.step("synthesizer", status="executed", executor="local", t0=t0, output=result,
                  summary=f"Dossier locale: {len(claims)} affermazioni, {len(checks)} limiti dichiarati.")
        return result

    def _validate_proposals(self, raw: object, ev_by_id: dict) -> tuple[list[dict], list[str]]:
        if not isinstance(raw, list):
            return [], []
        names = {e.name.lower(): e.id for e in self.db.scalars(select(Entity).where(Entity.owner_id == self.user.id))}
        out, issues = [], []
        for i, p in enumerate(raw[:20], start=1):
            if not isinstance(p, dict):
                continue
            a, b = names.get(str(p.get("source", "")).lower()), names.get(str(p.get("target", "")).lower())
            rt = p.get("relation_type")
            ev = [str(x) for x in (p.get("evidence") or []) if str(x) in ev_by_id]
            if not a or not b or a == b or rt not in RELATION_TYPES:
                issues.append(f"Relazione proposta {i} scartata: entità inesistenti o tipo non valido.")
                continue
            out.append({"source_entity_id": a, "target_entity_id": b, "source": p.get("source"), "target": p.get("target"),
                        "relation_type": rt, "evidence": ev, "rationale": str(p.get("rationale", ""))[:500]})
        return out, issues


def execute(db: Session, run: ResearchRun, user: User, settings: Settings, client: llm.LLMClient | None) -> ResearchRun:
    r = Runner(db, run, user, settings, client)
    run.status = "running"
    db.commit()
    try:
        plan = r.plan()
        run.plan = plan
        evidence, _ = r.research(plan)
        run.evidence = evidence
        db.commit()
        analyses = r.analysis(evidence)
        skeptic_claims, checks = r.skeptic(evidence, analyses)
        run.result = r.synthesize(evidence, analyses, skeptic_claims, checks)
        run.status = "awaiting_approval"
    except StepLimitExceeded as exc:
        run.status, run.error = "failed", str(exc)
    except Exception as exc:  # noqa: BLE001 - ogni errore resta visibile nel run
        run.status, run.error = "failed", f"{type(exc).__name__}: {exc}"
    run.finished_at = utcnow()
    db.commit()
    return run
