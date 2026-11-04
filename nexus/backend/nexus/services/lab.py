"""Economic Laboratory: esecuzione e archiviazione delle simulazioni."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..api import schemas_lab as S
from ..core.errors import ConfirmationRequiredError, NotFoundError, ValidationFailedError
from ..finance import analytics
from ..models import SimulationRun, User
from ..simulations import models as M
from . import activity, finance


def _save(db: Session, user: User, res: M.SimulationResult, params: dict) -> SimulationRun:
    run = SimulationRun(owner_id=user.id, kind=res.kind, title=res.title[:300], params=params, result=res.to_dict(), counterfactual=res.counterfactual)
    db.add(run)
    db.flush()
    activity.record(db, user=user, actor="user", action="simulation.run", entity_type="simulation", entity_id=run.id,
                    summary=f"Simulazione «{run.title}»" + (" (controfattuale)" if run.counterfactual else ""))
    db.commit()
    db.refresh(run)
    return run


def _guard(fn):
    try:
        return fn()
    except M.SimulationError as exc:
        raise ValidationFailedError(str(exc)) from exc


def run(db: Session, user: User, kind: str, data) -> SimulationRun:
    params = data.model_dump()
    if kind == "monte_carlo":
        res = _guard(lambda: M.monte_carlo_gbm(data.s0, data.mu, data.sigma, data.years, data.steps_per_year, data.n_paths, data.seed, data.threshold))
        if data.title:
            res.title = data.title
    elif kind == "monte_carlo_bootstrap":
        s = finance.get_series(db, user, data.series_id)
        obs = [(o.date, o.value) for o in s.observations if o.value is not None]
        res = _guard(lambda: M.monte_carlo_bootstrap(s.name, [d for d, _ in obs], [v for _, v in obs], analytics.PERIODS_PER_YEAR[s.frequency],
                                                     data.years, data.n_paths, data.block, data.seed))
    elif kind == "debt":
        res = _guard(lambda: M.debt_dynamics(**{k: v for k, v in params.items() if k != "title"}))
        if data.title:
            res.title = data.title
    elif kind == "sensitivity":
        b = data.base.model_dump()
        base = {k: b[k] for k in ("d0", "r_eff0", "r_market", "avg_maturity", "g", "pb", "years")}
        for k, (lo, hi) in data.ranges.items():
            if lo > hi:
                raise ValidationFailedError(f"Intervallo non valido per {k}: minimo > massimo.")
        res = _guard(lambda: M.sensitivity(base, dict(data.ranges)))
    elif kind == "inflation":
        res = _guard(lambda: M.inflation_scenarios(data.amount, data.nominal_rate, data.years, data.inflation_levels))
    elif kind == "monetary_policy":
        res = _guard(lambda: M.taylor_rules(data.inflation, data.output_gap, data.labels, [r.model_dump() for r in data.rules],
                                            data.r_star, data.pi_target, data.actual_rate))
    elif kind == "regression":
        res = _regression(db, user, data)
    elif kind == "backtest":
        s = finance.get_series(db, user, data.series_id)
        obs = [(o.date, o.value) for o in s.observations if o.value is not None]
        p = {"fast": data.fast, "slow": data.slow} if data.strategy == "ma_cross" else {"lookback": data.lookback} if data.strategy == "momentum" else {}
        res = _guard(lambda: M.backtest(s.name, [d for d, _ in obs], [v for _, v in obs], analytics.PERIODS_PER_YEAR[s.frequency],
                                        data.strategy, p, data.cost_bps, data.rf))
        res.data_used.append(f"Fonte: {s.source_label}")
    else:
        raise NotFoundError("Tipo di simulazione sconosciuto.")
    return _save(db, user, res, params)


def _regression(db: Session, user: User, data: S.RegressionIn) -> M.SimulationResult:
    if data.y_series_id in data.x_series_ids:
        raise ValidationFailedError("La variabile dipendente non può essere anche un regressore.")
    ys = finance.get_series(db, user, data.y_series_id)
    xs = [finance.get_series(db, user, i) for i in data.x_series_ids]
    freqs = {s.frequency for s in [ys, *xs]}
    if len(freqs) > 1 and data.target_frequency is None:
        raise ValidationFailedError(f"Frequenze diverse ({', '.join(sorted(freqs))}): scegli esplicitamente una frequenza comune e un metodo.")
    target = data.target_frequency or freqs.pop()
    procedure = []

    def prep(s):
        series = analytics.to_pandas([(o.date, o.value) for o in s.observations])
        if s.frequency != target:
            try:
                series = analytics.resample(series, s.frequency, target, data.method)
            except analytics.AnalysisError as exc:
                raise ValidationFailedError(str(exc)) from exc
            procedure.append(f"«{s.name}» ricampionata da {s.frequency} a {target} ({data.method})")
        return series

    y = prep(ys)
    x_map = {s.name: prep(s) for s in xs}
    used = [f"{s.name} — {s.source_label}" for s in [ys, *xs]]
    return _guard(lambda: M.regression(ys.name, y, x_map, data.transform, data.lags, used, procedure))


def list_runs(db: Session, user: User, kind: str | None = None) -> list[SimulationRun]:
    stmt = select(SimulationRun).where(SimulationRun.owner_id == user.id)
    if kind:
        stmt = stmt.where(SimulationRun.kind == kind)
    return list(db.scalars(stmt.order_by(SimulationRun.id.desc()).limit(200)))


def get(db: Session, user: User, sim_id: int) -> SimulationRun:
    r = db.get(SimulationRun, sim_id)
    if r is None or r.owner_id != user.id:
        raise NotFoundError("Simulazione non trovata.")
    return r


def delete(db: Session, user: User, sim_id: int, confirm: bool) -> None:
    r = get(db, user, sim_id)
    if not confirm:
        raise ConfirmationRequiredError("Eliminare una simulazione richiede conferma (confirm=true).")
    db.delete(r)
    db.commit()
