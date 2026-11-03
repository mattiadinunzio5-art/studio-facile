"""Connettori a fonti di dati aperte.

Ogni connettore restituisce osservazioni *così come pubblicate* dalla fonte,
più i metadati di provenienza (nome, unità, frequenza, ultimo aggiornamento
dichiarato dalla fonte, URL, licenza). Nessun valore viene stimato o riempito.

Cache: le risposte sono salvate su disco; se la fonte non è raggiungibile si
usa la copia in cache (segnalata come tale). Le chiavi API non entrano mai
nella chiave di cache né nei log.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import httpx

USER_AGENT = "NEXUS/0.1 (open-data research platform)"


class ConnectorError(Exception):
    pass


@dataclass
class FetchResult:
    name: str
    unit: str
    frequency: str
    source_label: str
    source_url: str
    license_note: str
    source_last_updated: str
    observations: list[tuple[str, float | None]]
    description: str = ""
    country: str = ""
    from_cache: bool = False
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(UTC))


# --- Date --------------------------------------------------------------------

_PATTERNS = [
    (re.compile(r"^(\d{4})$"), "A", lambda m: f"{m[1]}-01-01"),
    (re.compile(r"^(\d{4})-?Q([1-4])$"), "Q", lambda m: f"{m[1]}-{(int(m[2]) - 1) * 3 + 1:02d}-01"),
    (re.compile(r"^(\d{4})-?M?(\d{2})$"), "M", lambda m: f"{m[1]}-{m[2]}-01"),
    (re.compile(r"^(\d{4})-(\d{2})-(\d{2})$"), "D", lambda m: f"{m[1]}-{m[2]}-{m[3]}"),
]


def parse_period(label: str) -> tuple[str, str]:
    """Converte un'etichetta di periodo in (data inizio periodo, frequenza)."""
    label = label.strip()
    for rx, freq, conv in _PATTERNS:
        m = rx.match(label)
        if m:
            iso = conv(m)
            mo = int(iso[5:7])
            if not 1 <= mo <= 12:
                break
            if freq == "D":
                datetime.strptime(iso, "%Y-%m-%d")  # valida il giorno
            return iso, freq
    raise ConnectorError(f"Periodo non riconosciuto: '{label}'")


def infer_frequency(dates: list[str]) -> str:
    """Frequenza dalla spaziatura mediana tra le date (per serie giornaliere/settimanali)."""
    if len(dates) < 3:
        return "D"
    ds = sorted(datetime.strptime(d, "%Y-%m-%d") for d in dates)
    gaps = sorted((b - a).days for a, b in zip(ds, ds[1:]))
    med = gaps[len(gaps) // 2]
    if med <= 4:
        return "D"
    if med <= 10:
        return "W"
    if med <= 40:
        return "M"
    if med <= 120:
        return "Q"
    return "A"


def _to_float(v) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if s in ("", ".", "NA", "N/A", "nan", "NaN", ":", "-"):
        return None
    try:
        return float(s.replace(",", ".") if s.count(",") == 1 and "." not in s else s.replace(",", ""))
    except ValueError:
        return None


# --- Cache -------------------------------------------------------------------


class Cache:
    def __init__(self, directory: Path, ttl_hours: int):
        self.dir = directory
        self.ttl = ttl_hours * 3600

    def _path(self, key: str) -> Path:
        return self.dir / f"{hashlib.sha256(key.encode()).hexdigest()}.json"

    def get(self, key: str, allow_stale: bool = False) -> tuple[str, float] | None:
        p = self._path(key)
        if not p.exists():
            return None
        data = json.loads(p.read_text())
        if not allow_stale and time.time() - data["fetched_at"] > self.ttl:
            return None
        return data["payload"], data["fetched_at"]

    def put(self, key: str, payload: str) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        self._path(key).write_text(json.dumps({"fetched_at": time.time(), "payload": payload}))


class HttpFetcher:
    def __init__(self, cache: Cache, timeout: float = 30.0, client: httpx.Client | None = None):
        self.cache = cache
        self.client = client or httpx.Client(timeout=timeout, follow_redirects=True, headers={"User-Agent": USER_AGENT})

    def get(self, url: str, params: dict | None = None, cache_key: str | None = None, force: bool = False) -> tuple[str, bool, datetime]:
        key = cache_key or (url + "?" + json.dumps(params or {}, sort_keys=True))
        if not force:
            hit = self.cache.get(key)
            if hit:
                return hit[0], True, datetime.fromtimestamp(hit[1], UTC)
        try:
            r = self.client.get(url, params=params)
        except httpx.HTTPError as exc:
            stale = self.cache.get(key, allow_stale=True)
            if stale:
                return stale[0], True, datetime.fromtimestamp(stale[1], UTC)
            raise ConnectorError(f"Fonte non raggiungibile ({type(exc).__name__}) e nessuna copia in cache.") from exc
        if r.status_code >= 400:
            stale = self.cache.get(key, allow_stale=True)
            if stale and r.status_code >= 500:
                return stale[0], True, datetime.fromtimestamp(stale[1], UTC)
            raise ConnectorError(f"La fonte ha risposto HTTP {r.status_code}: {r.text[:200]}")
        self.cache.put(key, r.text)
        return r.text, False, datetime.now(UTC)


# --- World Bank ----------------------------------------------------------------

_UNIT_HINTS = ("%", "US$", "LCU", "index", "per ", "constant", "current", "number", "tons", "kg")


def unit_from_name(name: str) -> str:
    """Unità dalle parentesi del nome World Bank (es. '(% of GDP)'), ignorando note come '(modeled ILO estimate)'."""
    for group in re.findall(r"\(([^)]*)\)", name):
        if any(h.lower() in group.lower() for h in _UNIT_HINTS):
            return group
    return ""


def trim_coverage(obs: list[tuple[str, float | None]]) -> list[tuple[str, float | None]]:
    """Rimuove i periodi vuoti prima del primo e dopo l'ultimo valore pubblicato.

    Alcune fonti restituiscono l'intero intervallo di anni anche fuori dalla
    copertura della serie: quelli non sono «dati mancanti». I vuoti interni restano.
    """
    idx = [i for i, (_, v) in enumerate(obs) if v is not None]
    if not idx:
        return []
    return obs[idx[0] : idx[-1] + 1]

WB_LICENSE = "World Bank Open Data — licenza indicata per dataset (spesso CC BY 4.0). Verificare: https://www.worldbank.org/en/about/legal/terms-of-use-for-datasets"


def fetch_world_bank(f: HttpFetcher, indicator: str, country: str, force: bool = False) -> FetchResult:
    if not re.fullmatch(r"[A-Za-z0-9._]{2,60}", indicator) or not re.fullmatch(r"[A-Za-z0-9]{2,3}", country):
        raise ConnectorError("Codice indicatore o paese non valido.")
    base = "https://api.worldbank.org/v2"
    meta_txt, _, _ = f.get(f"{base}/indicator/{indicator}", {"format": "json"}, force=force)
    meta = json.loads(meta_txt)
    if not isinstance(meta, list) or len(meta) < 2 or not meta[1]:
        raise ConnectorError("Indicatore World Bank inesistente.")
    info = meta[1][0]
    txt, cached, when = f.get(f"{base}/country/{country}/indicator/{indicator}", {"format": "json", "per_page": 20000}, force=force)
    data = json.loads(txt)
    if not isinstance(data, list) or len(data) < 2:
        msg = data[0].get("message", [{}])[0].get("value", "") if isinstance(data, list) and data else ""
        raise ConnectorError(f"Nessun dato World Bank per {country}/{indicator}. {msg}".strip())
    rows = data[1] or []
    obs, freqs = [], set()
    for r in rows:
        iso, fr = parse_period(r["date"])
        freqs.add(fr)
        obs.append((iso, _to_float(r.get("value"))))
    if len(freqs) > 1:
        raise ConnectorError("La serie contiene frequenze miste: non importata.")
    name = info.get("name", indicator)
    country_name = rows[0]["country"]["value"] if rows else country
    unit = info.get("unit") or unit_from_name(name)
    return FetchResult(
        name=f"{name} — {country_name}", unit=unit, frequency=freqs.pop() if freqs else "A",
        source_label=f"World Bank, {info.get('source', {}).get('value', 'WDI')} ({info.get('sourceOrganization', '')[:200]})".strip(),
        source_url=f"https://data.worldbank.org/indicator/{indicator}?locations={country}", license_note=WB_LICENSE,
        source_last_updated=data[0].get("lastupdated", ""), observations=sorted(obs), description=info.get("sourceNote", "")[:4000],
        country=country_name, from_cache=cached, retrieved_at=when,
    )


# --- FRED --------------------------------------------------------------------

FRED_FREQ = {"D": "D", "W": "W", "BW": "W", "M": "M", "Q": "Q", "SA": "Q", "A": "A"}
FRED_LICENSE = "FRED (Federal Reserve Bank of St. Louis): alcune serie sono di terzi e protette da copyright. Verificare: https://fred.stlouisfed.org/legal/"


def fetch_fred(f: HttpFetcher, series_id: str, api_key: str | None, force: bool = False) -> FetchResult:
    if not api_key:
        raise ConnectorError("FRED richiede una chiave API gratuita: configurala in Sistema → Credenziali.")
    if not re.fullmatch(r"[A-Za-z0-9_.]{1,40}", series_id):
        raise ConnectorError("ID serie FRED non valido.")
    base = "https://api.stlouisfed.org/fred"
    common = {"series_id": series_id, "file_type": "json"}
    meta_txt, _, _ = f.get(f"{base}/series", {**common, "api_key": api_key}, cache_key=f"fred-meta-{series_id}", force=force)
    meta = json.loads(meta_txt).get("seriess", [])
    if not meta:
        raise ConnectorError("Serie FRED inesistente.")
    m = meta[0]
    txt, cached, when = f.get(f"{base}/series/observations", {**common, "api_key": api_key}, cache_key=f"fred-obs-{series_id}", force=force)
    obs = [(o["date"], _to_float(o["value"])) for o in json.loads(txt).get("observations", [])]
    return FetchResult(
        name=m.get("title", series_id), unit=m.get("units", ""), frequency=FRED_FREQ.get(m.get("frequency_short", ""), "M"),
        source_label=f"FRED, Federal Reserve Bank of St. Louis — serie {series_id}", source_url=f"https://fred.stlouisfed.org/series/{series_id}",
        license_note=FRED_LICENSE, source_last_updated=m.get("last_updated", ""), observations=obs, description=m.get("notes", "")[:4000],
        from_cache=cached, retrieved_at=when,
    )


# --- Our World in Data -------------------------------------------------------------

OWID_LICENSE = "Our World in Data: grafici CC BY; i dati di terze parti restano soggetti alle licenze delle fonti originali indicate."


def fetch_owid(f: HttpFetcher, slug: str, entity: str, force: bool = False) -> FetchResult:
    if not re.fullmatch(r"[a-z0-9-]{2,120}", slug):
        raise ConnectorError("Slug OWID non valido (es. 'inflation-of-consumer-prices').")
    base = f"https://ourworldindata.org/grapher/{slug}"
    q = {"v": "1", "csvType": "full", "useColumnShortNames": "true"}
    meta = json.loads(f.get(f"{base}.metadata.json", q, force=force)[0])
    txt, cached, when = f.get(f"{base}.csv", q, force=force)
    reader = csv.DictReader(io.StringIO(txt))
    cols = [c for c in (reader.fieldnames or []) if c not in ("entity", "code", "year", "day")]
    if not cols:
        raise ConnectorError("Formato OWID inatteso.")
    col = cols[0]
    time_col = "day" if "day" in (reader.fieldnames or []) else "year"
    obs, freq = [], "A"
    for row in reader:
        if row["entity"].lower() == entity.lower() or (row.get("code") or "").lower() == entity.lower():
            if time_col == "year":
                iso = f"{int(row['year']):04d}-01-01" if int(row["year"]) > 0 else None
            else:
                iso, freq = row["day"], "D"
            if iso:
                obs.append((iso, _to_float(row[col])))
    if not obs:
        raise ConnectorError(f"Entità '{entity}' non presente nel dataset OWID.")
    cmeta = meta.get("columns", {}).get(col, {})
    if freq == "D":
        freq = infer_frequency([d for d, _ in obs])
    return FetchResult(
        name=f"{cmeta.get('titleShort') or meta.get('chart', {}).get('title', slug)} — {entity}", unit=cmeta.get("unit", ""),
        frequency=freq, source_label=cmeta.get("citationShort") or "Our World in Data", source_url=f"https://ourworldindata.org/grapher/{slug}",
        license_note=OWID_LICENSE, source_last_updated=cmeta.get("lastUpdated", ""), observations=sorted(obs),
        description=meta.get("chart", {}).get("subtitle", "")[:4000], country=entity, from_cache=cached, retrieved_at=when,
    )


# --- Eurostat ----------------------------------------------------------------

EUROSTAT_LICENSE = "Eurostat: riutilizzo consentito con citazione della fonte, salvo eccezioni. Verificare: https://ec.europa.eu/eurostat/about-us/policies/copyright"


def parse_jsonstat(d: dict) -> tuple[list[tuple[str, float | None]], dict]:
    ids, sizes = d["id"], d["size"]
    if 0 in sizes:
        raise ConnectorError("I filtri non selezionano alcun dato (controlla i codici delle dimensioni).")
    multi = [i for i, s in zip(ids, sizes) if s > 1 and i != "time"]
    if multi:
        raise ConnectorError(f"I filtri selezionano più serie: specifica un solo valore per {', '.join(multi)}.")
    t_index = d["dimension"]["time"]["category"]["index"]
    # Con tutte le altre dimensioni a 1 elemento l'indice piatto coincide con quello del tempo.
    values = d.get("value", {})
    obs = []
    for label, pos in sorted(t_index.items(), key=lambda x: x[1]):
        v = values.get(str(pos)) if isinstance(values, dict) else (values[pos] if pos < len(values) else None)
        obs.append((label, _to_float(v)))
    labels = {i: next(iter(d["dimension"][i]["category"]["label"].values()), "") for i in ids if i != "time"}
    return obs, labels


def fetch_eurostat(f: HttpFetcher, dataset: str, filters: dict[str, str], force: bool = False) -> FetchResult:
    if not re.fullmatch(r"[a-z0-9_]{2,40}", dataset):
        raise ConnectorError("Codice dataset Eurostat non valido.")
    for k, v in filters.items():
        if not re.fullmatch(r"[a-z_]{1,20}", k) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,40}", v):
            raise ConnectorError(f"Filtro non valido: {k}={v}")
    url = f"https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{dataset}"
    txt, cached, when = f.get(url, {**filters, "format": "JSON", "lang": "EN"}, force=force)
    d = json.loads(txt)
    if "error" in d:
        raise ConnectorError(f"Eurostat: {d['error']}")
    raw, labels = parse_jsonstat(d)
    obs, freqs = [], set()
    for label, v in raw:
        iso, fr = parse_period(label)
        freqs.add(fr)
        obs.append((iso, v))
    if len(freqs) > 1:
        raise ConnectorError("Frequenze miste nella risposta Eurostat.")
    flt = ", ".join(f"{k}={v}" for k, v in sorted(filters.items()))
    return FetchResult(
        name=f"{d.get('label', dataset)} — {labels.get('geo', '')}".strip(" —"), unit=labels.get("unit", ""),
        frequency=freqs.pop() if freqs else "A", source_label=f"Eurostat, dataset {dataset} ({flt})",
        source_url=f"https://ec.europa.eu/eurostat/databrowser/view/{dataset}/default/table", license_note=EUROSTAT_LICENSE,
        source_last_updated=d.get("updated", ""), observations=obs, description="; ".join(f"{k}: {v}" for k, v in labels.items()),
        country=labels.get("geo", ""), from_cache=cached, retrieved_at=when,
    )


# --- CSV dell'utente -----------------------------------------------------------


def parse_user_csv(text: str, date_col: str | None = None, value_col: str | None = None) -> tuple[list[tuple[str, float | None]], str, list[str]]:
    """CSV con colonne data/valore. Restituisce osservazioni, frequenza e avvisi."""
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    fields = reader.fieldnames or []
    if len(fields) < 2:
        raise ConnectorError("Il CSV deve avere almeno due colonne (data, valore).")
    dc = date_col or fields[0]
    vc = value_col or fields[1]
    if dc not in fields or vc not in fields:
        raise ConnectorError(f"Colonne non trovate. Disponibili: {', '.join(fields)}")
    obs, freqs, warnings, seen = [], set(), [], set()
    for i, row in enumerate(reader, start=2):
        raw = (row.get(dc) or "").strip()
        try:
            iso, fr = parse_period(raw)
        except (ConnectorError, ValueError):
            raise ConnectorError(f"Data non valida alla riga {i}: '{raw}'") from None
        if iso in seen:
            raise ConnectorError(f"Data duplicata alla riga {i}: {raw}")
        seen.add(iso)
        freqs.add(fr)
        v = _to_float(row.get(vc))
        if v is None and (row.get(vc) or "").strip() not in ("", ".", "NA", "N/A", ":", "-", "nan", "NaN"):
            warnings.append(f"Riga {i}: valore non numerico '{row.get(vc)}' trattato come mancante")
        obs.append((iso, v))
    if not obs:
        raise ConnectorError("Il CSV non contiene righe.")
    if len(freqs) > 1:
        raise ConnectorError("Il CSV mescola formati di periodo diversi (es. anni e mesi): uniformali prima dell'importazione.")
    freq = freqs.pop()
    if freq == "D":
        freq = infer_frequency([d for d, _ in obs])
    return sorted(obs), freq, warnings
