"""Analisi quantitative su serie storiche (pandas / NumPy / statsmodels).

Regole:
- Le statistiche si calcolano solo sui valori osservati; i mancanti sono contati
  e mai interpolati.
- Serie con frequenze diverse non vengono confrontate senza un ricampionamento
  esplicito richiesto dall'utente (frequenza e metodo dichiarati nel risultato).
- Ogni risultato riporta il numero di osservazioni usate.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

PERIODS_PER_YEAR = {"D": 252, "W": 52, "M": 12, "Q": 4, "A": 1}
FREQ_ORDER = {"D": 0, "W": 1, "M": 2, "Q": 3, "A": 4}
PANDAS_RULE = {"W": "W-FRI", "M": "MS", "Q": "QS", "A": "YS"}


class AnalysisError(ValueError):
    pass


def to_pandas(observations: list[tuple[str, float | None]]) -> pd.Series:
    if not observations:
        return pd.Series(dtype=float)
    idx = pd.to_datetime([d for d, _ in observations])
    s = pd.Series([np.nan if v is None else v for _, v in observations], index=idx, dtype=float)
    return s.sort_index()


def _f(x) -> float | None:
    if x is None:
        return None
    x = float(x)
    return None if math.isnan(x) or math.isinf(x) else round(x, 10)


def _points(s: pd.Series) -> list[dict]:
    return [{"date": d.strftime("%Y-%m-%d"), "value": _f(v)} for d, v in s.items()]


def returns(s: pd.Series, kind: str = "simple") -> pd.Series:
    """Rendimenti tra osservazioni consecutive *valide* (i buchi non vengono colmati)."""
    v = s.dropna()
    if kind == "log":
        if (v <= 0).any():
            raise AnalysisError("Rendimenti logaritmici non definiti per valori ≤ 0.")
        return np.log(v / v.shift(1)).dropna()
    prev = v.shift(1)
    r = (v - prev) / prev.abs()
    return r.replace([np.inf, -np.inf], np.nan).dropna()


def drawdown(s: pd.Series) -> tuple[pd.Series, dict]:
    v = s.dropna()
    if v.empty:
        return v, {}
    if (v <= 0).any():
        raise AnalysisError("Drawdown definito solo per serie di livelli positivi (prezzi, indici).")
    peak = v.cummax()
    dd = v / peak - 1
    trough = dd.idxmin()
    peak_date = v.loc[:trough].idxmax()
    after = v.loc[trough:]
    recovered = after[after >= v.loc[peak_date]]
    return dd, {
        "max_drawdown": _f(dd.min()),
        "peak_date": peak_date.strftime("%Y-%m-%d"),
        "trough_date": trough.strftime("%Y-%m-%d"),
        "recovery_date": recovered.index[0].strftime("%Y-%m-%d") if len(recovered) else None,
    }


def anomalies(s: pd.Series, z: float = 4.0) -> list[dict]:
    """Variazioni anomale (z robusto > soglia): segnalate, mai rimosse.

    Si usa uno z-score robusto (mediana e MAD) perché con la deviazione standard
    un singolo valore estremo gonfia la dispersione e nasconde sé stesso.
    """
    diffs = s.dropna().diff().dropna()
    if len(diffs) < 10:
        return []
    med = diffs.median()
    dev = (diffs - med).abs()
    scale = 1.4826 * dev.median()
    if scale == 0:
        scale = dev.mean()
    if scale == 0:
        return []
    zs = (diffs - med) / scale
    return [{"date": d.strftime("%Y-%m-%d"), "change": _f(diffs[d]), "z": _f(zs[d])} for d in zs[zs.abs() > z].index]


@dataclass
class SeriesInput:
    id: int
    name: str
    frequency: str
    unit: str
    observations: list[tuple[str, float | None]]


def analyze(series: SeriesInput, ma_windows: list[int], return_kind: str = "simple", level_metrics: bool = True) -> dict:
    s = to_pandas(series.observations)
    valid = s.dropna()
    if len(valid) < 2:
        raise AnalysisError("Servono almeno 2 osservazioni valide.")
    ppy = PERIODS_PER_YEAR[series.frequency]
    out: dict = {
        "series_id": series.id,
        "frequency": series.frequency,
        "summary": {
            "observations": int(len(s)), "valid": int(len(valid)), "missing": int(s.isna().sum()),
            "first_date": valid.index[0].strftime("%Y-%m-%d"), "last_date": valid.index[-1].strftime("%Y-%m-%d"),
            "first_value": _f(valid.iloc[0]), "last_value": _f(valid.iloc[-1]), "min": _f(valid.min()), "max": _f(valid.max()),
            "mean": _f(valid.mean()), "std": _f(valid.std()), "median": _f(valid.median()),
        },
        "warnings": [],
    }
    r = returns(s, return_kind) if level_metrics else valid.diff().dropna()
    if level_metrics:
        total = valid.iloc[-1] / valid.iloc[0] - 1 if valid.iloc[0] > 0 else None
        years = (valid.index[-1] - valid.index[0]).days / 365.25
        cagr = (valid.iloc[-1] / valid.iloc[0]) ** (1 / years) - 1 if years > 0 and valid.iloc[0] > 0 and valid.iloc[-1] > 0 else None
        out["returns"] = {
            "kind": return_kind, "count": int(len(r)), "mean_per_period": _f(r.mean()), "volatility_per_period": _f(r.std()),
            "volatility_annualized": _f(r.std() * math.sqrt(ppy)) if len(r) > 1 else None, "annualization_factor": ppy,
            "total_change": _f(total), "cagr": _f(cagr), "best": _f(r.max()), "worst": _f(r.min()),
        }
        try:
            dd, dd_stats = drawdown(s)
            out["drawdown"] = dd_stats
            out["drawdown_series"] = _points(dd)
        except AnalysisError as exc:
            out["warnings"].append(str(exc))
    else:
        out["changes"] = {"count": int(len(r)), "mean": _f(r.mean()), "std": _f(r.std()), "unit": f"variazione assoluta ({series.unit})"}
    out["returns_series"] = _points(r)
    out["moving_averages"] = {}
    for w in ma_windows:
        if w >= len(valid):
            out["warnings"].append(f"Media mobile a {w} periodi non calcolabile: solo {len(valid)} osservazioni valide.")
            continue
        out["moving_averages"][str(w)] = _points(valid.rolling(w).mean().dropna())
    an = anomalies(s)
    if an:
        out["warnings"].append(f"{len(an)} variazioni anomale (z robusto > 4): verificare se sono errori di dato o eventi reali.")
    out["anomalies"] = an
    out["timeseries"] = timeseries_tests(valid)
    if out["summary"]["missing"]:
        out["warnings"].append(f"{out['summary']['missing']} osservazioni mancanti: escluse dai calcoli, non interpolate.")
    return out


def timeseries_tests(v: pd.Series) -> dict:
    from statsmodels.tsa.stattools import acf, adfuller

    res: dict = {}
    n = len(v)
    t = np.arange(n, dtype=float)
    slope, intercept = np.polyfit(t, v.values, 1)
    res["linear_trend"] = {"slope_per_period": _f(slope), "intercept": _f(intercept), "method": "OLS su indice temporale"}
    if n >= 12:
        try:
            stat, p, lags, nobs, crit, _ = adfuller(v.values, autolag="AIC", result_object=False)
            res["adf"] = {
                "statistic": _f(stat), "p_value": _f(p), "lags": int(lags), "nobs": int(nobs),
                "critical_values": {k: _f(x) for k, x in crit.items()},
                "interpretation": "Si rifiuta la radice unitaria al 5% (serie compatibile con stazionarietà)" if p < 0.05
                else "Non si rifiuta la radice unitaria al 5% (serie probabilmente non stazionaria)",
            }
        except (ValueError, np.linalg.LinAlgError) as exc:
            res["adf"] = {"error": str(exc)}
        nlags = min(12, n // 2 - 1)
        res["acf"] = [_f(x) for x in acf(v.values, nlags=nlags, fft=False)]
    else:
        res["note"] = "Test ADF e autocorrelazione richiedono almeno 12 osservazioni."
    return res


def resample(s: pd.Series, source_freq: str, target_freq: str, method: str) -> pd.Series:
    """Ricampionamento esplicito. Consentito solo verso frequenze più basse."""
    if FREQ_ORDER[target_freq] < FREQ_ORDER[source_freq]:
        raise AnalysisError(
            f"Ricampionamento da {source_freq} a {target_freq} non consentito: creerebbe dati inesistenti (interpolazione)."
        )
    if target_freq == source_freq:
        return s
    rule = PANDAS_RULE[target_freq]
    g = s.dropna().resample(rule)
    if method == "last":
        out = g.last()
    elif method == "mean":
        out = g.mean()
    elif method == "sum":
        out = g.sum(min_count=1)
    else:
        raise AnalysisError("Metodo di ricampionamento non valido (last, mean, sum).")
    if target_freq == "W":
        out.index = out.index - pd.Timedelta(days=4)  # inizio settimana (lunedì)
    return out


def compare(inputs: list[SeriesInput], target_freq: str | None, method: str, mode: str) -> dict:
    if len(inputs) < 2:
        raise AnalysisError("Servono almeno due serie.")
    freqs = {i.frequency for i in inputs}
    procedure = []
    if len(freqs) > 1 and target_freq is None:
        raise AnalysisError(
            f"Le serie hanno frequenze diverse ({', '.join(sorted(freqs))}). Scegli esplicitamente una frequenza comune e un metodo di aggregazione."
        )
    target = target_freq or freqs.pop()
    frames = {}
    for i in inputs:
        s = to_pandas(i.observations)
        if i.frequency != target:
            s = resample(s, i.frequency, target, method)
            procedure.append(f"«{i.name}»: da {i.frequency} a {target} con metodo '{method}'")
        frames[str(i.id)] = s
    df = pd.DataFrame(frames).dropna()
    if len(df) < 3:
        raise AnalysisError("Meno di 3 date comuni con valori validi: confronto non significativo.")
    if mode == "returns":
        cols = {}
        for c in df.columns:
            if (df[c] <= 0).any():
                cols[c] = df[c].diff()
                procedure.append(f"Serie {c}: valori ≤ 0, usate differenze assolute invece dei rendimenti")
            else:
                cols[c] = df[c].pct_change()
        basis = pd.DataFrame(cols).dropna()
    else:
        basis = df
    corr = basis.corr(method="pearson")
    rebased = {}
    for c in df.columns:
        first = df[c].iloc[0]
        rebased[c] = _points(df[c] / first * 100) if first > 0 else None
    return {
        "frequency": target, "common_observations": int(len(df)), "basis": mode,
        "period": {"start": df.index[0].strftime("%Y-%m-%d"), "end": df.index[-1].strftime("%Y-%m-%d")},
        "procedure": procedure or ["Nessun ricampionamento: stessa frequenza."],
        "correlation": {a: {b: _f(corr.loc[a, b]) for b in corr.columns} for a in corr.index},
        "aligned": {c: _points(df[c]) for c in df.columns},
        "rebased_100": rebased,
        "notes": [
            "Correlazione di Pearson su " + ("variazioni periodali" if mode == "returns" else "livelli") + f", {len(basis)} osservazioni comuni.",
            "La correlazione tra livelli di serie con trend è spesso spuria: preferire le variazioni." if mode == "levels" else
            "Correlazione non implica causalità.",
        ],
    }
