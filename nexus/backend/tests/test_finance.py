"""Test di Financial Intelligence con risposte HTTP simulate (formato reale delle fonti)."""

import json

import httpx
import numpy as np
import pandas as pd
import pytest

from nexus.finance import analytics, connectors


def fetcher(tmp_path, handler):
    return connectors.HttpFetcher(connectors.Cache(tmp_path / "cache", 24), client=httpx.Client(transport=httpx.MockTransport(handler)))


WB_META = [{"page": 1}, [{"id": "FP.CPI.TOTL.ZG", "name": "Inflation, consumer prices (annual %)", "unit": "",
                          "source": {"value": "World Development Indicators"}, "sourceNote": "Nota", "sourceOrganization": "IMF IFS"}]]
WB_DATA = [{"page": 1, "lastupdated": "2026-10-08"}, [
    {"country": {"value": "Italy"}, "date": "2024", "value": 0.98},
    {"country": {"value": "Italy"}, "date": "2023", "value": 5.6},
    {"country": {"value": "Italy"}, "date": "2022", "value": None},
]]


def wb_handler(req):
    return httpx.Response(200, json=WB_META if "/indicator/FP" in req.url.path and "/country/" not in req.url.path else WB_DATA)


# --- Connettori ---------------------------------------------------------------------


def test_parse_period():
    assert connectors.parse_period("1999") == ("1999-01-01", "A")
    assert connectors.parse_period("2020Q3") == ("2020-07-01", "Q")
    assert connectors.parse_period("2020-Q1") == ("2020-01-01", "Q")
    assert connectors.parse_period("2020M02") == ("2020-02-01", "M")
    assert connectors.parse_period("2020-11") == ("2020-11-01", "M")
    for bad in ("2020-13", "20x0", "2021-02-30", ""):
        with pytest.raises((connectors.ConnectorError, ValueError)):
            connectors.parse_period(bad)


def test_world_bank_parsing(tmp_path):
    r = connectors.fetch_world_bank(fetcher(tmp_path, wb_handler), "FP.CPI.TOTL.ZG", "ITA")
    assert r.frequency == "A" and r.source_last_updated == "2026-10-08"
    assert r.observations == [("2022-01-01", None), ("2023-01-01", 5.6), ("2024-01-01", 0.98)]
    assert r.unit == "annual %" and "Italy" in r.name and "World Bank" in r.source_label


def test_unit_and_coverage_helpers():
    assert connectors.unit_from_name("Unemployment, total (% of total labor force) (modeled ILO estimate)") == "% of total labor force"
    assert connectors.unit_from_name("Something (note only)") == ""
    obs = [("1960", None), ("1961", 1.0), ("1962", None), ("1963", 2.0), ("1964", None)]
    assert connectors.trim_coverage(obs) == obs[1:4]
    assert connectors.trim_coverage([("1", None)]) == []


def test_offline_source_uses_stale_cache(tmp_path):
    connectors.fetch_world_bank(fetcher(tmp_path, wb_handler), "FP.CPI.TOTL.ZG", "ITA")

    def offline(_):
        raise httpx.ConnectError("offline")

    r = connectors.fetch_world_bank(fetcher(tmp_path, offline), "FP.CPI.TOTL.ZG", "ITA", force=True)
    assert r.from_cache is True and len(r.observations) == 3


def test_offline_without_cache_fails_cleanly(tmp_path):
    def offline(_):
        raise httpx.ConnectError("offline")

    with pytest.raises(connectors.ConnectorError, match="non raggiungibile"):
        connectors.fetch_world_bank(fetcher(tmp_path, offline), "FP.CPI.TOTL.ZG", "ITA")


def test_fred_requires_key_and_hides_it_from_cache(tmp_path):
    with pytest.raises(connectors.ConnectorError, match="chiave"):
        connectors.fetch_fred(fetcher(tmp_path, lambda r: httpx.Response(200)), "UNRATE", None)

    def h(req):
        if req.url.path.endswith("/observations"):
            return httpx.Response(200, json={"observations": [{"date": "2020-01-01", "value": "3.5"}, {"date": "2020-02-01", "value": "."}]})
        return httpx.Response(200, json={"seriess": [{"title": "Unemployment Rate", "units": "Percent", "frequency_short": "M", "last_updated": "2026-10-01"}]})

    r = connectors.fetch_fred(fetcher(tmp_path, h), "UNRATE", "SEGRETO123")
    assert r.observations == [("2020-01-01", 3.5), ("2020-02-01", None)] and r.frequency == "M"
    for f in (tmp_path / "cache").iterdir():
        assert "SEGRETO123" not in f.read_text() and "SEGRETO123" not in f.name


def test_eurostat_jsonstat_parsing():
    d = {"id": ["freq", "unit", "geo", "time"], "size": [1, 1, 1, 3],
         "dimension": {"freq": {"category": {"label": {"A": "Annual"}}}, "unit": {"category": {"label": {"RCH_A_AVG": "Annual average rate of change"}}},
                       "geo": {"category": {"label": {"IT": "Italy"}}}, "time": {"category": {"index": {"2021": 0, "2022": 1, "2023": 2}}}},
         "value": {"0": 1.9, "2": 5.9}}
    obs, labels = connectors.parse_jsonstat(d)
    assert obs == [("2021", 1.9), ("2022", None), ("2023", 5.9)] and labels["geo"] == "Italy"
    d["size"] = [1, 2, 1, 3]
    with pytest.raises(connectors.ConnectorError, match="più serie"):
        connectors.parse_jsonstat(d)
    d["size"] = [1, 0, 1, 3]
    with pytest.raises(connectors.ConnectorError, match="non selezionano"):
        connectors.parse_jsonstat(d)


def test_owid_parsing(tmp_path):
    def h(req):
        if req.url.path.endswith(".json"):
            return httpx.Response(200, json={"chart": {"title": "Inflation"}, "columns": {"infl": {"titleShort": "Inflation", "unit": "%", "lastUpdated": "2026-07-27", "citationShort": "IMF via WB – processed by OWID"}}})
        return httpx.Response(200, text="entity,code,year,infl\nItaly,ITA,2020,-0.1\nItaly,ITA,2021,1.9\nFrance,FRA,2021,1.6\n")

    r = connectors.fetch_owid(fetcher(tmp_path, h), "inflation", "Italy")
    assert r.observations == [("2020-01-01", -0.1), ("2021-01-01", 1.9)] and r.source_last_updated == "2026-07-27"
    with pytest.raises(connectors.ConnectorError, match="non presente"):
        connectors.fetch_owid(fetcher(tmp_path, h), "inflation", "Atlantide")


def test_user_csv_validation():
    obs, freq, warn = connectors.parse_user_csv("data;valore\n2020-01;1,5\n2020-02;\n2020-03;abc\n")
    assert freq == "M" and obs[0] == ("2020-01-01", 1.5) and obs[1][1] is None and len(warn) == 1
    for bad, msg in [("data,valore\n2020,1\n2020-02,2\n", "mescola"), ("data,valore\n2020-02-30,1\n", "Data non valida"),
                     ("data,valore\n2020,1\n2020,2\n", "duplicata"), ("data\n2020\n", "due colonne")]:
        with pytest.raises(connectors.ConnectorError, match=msg):
            connectors.parse_user_csv(bad)


# --- Analisi ------------------------------------------------------------------------------


def series_input(values, freq="A", start=2000, sid=1):
    dates = pd.date_range(f"{start}-01-01", periods=len(values), freq={"A": "YS", "M": "MS", "Q": "QS", "D": "B"}[freq])
    return analytics.SeriesInput(sid, f"s{sid}", freq, "", [(d.strftime("%Y-%m-%d"), v) for d, v in zip(dates, values)])


def test_returns_volatility_drawdown_known_values():
    res = analytics.analyze(series_input([100, 110, 99, 120], "A"), [2])
    r = res["returns"]
    assert r["count"] == 3 and r["total_change"] == pytest.approx(0.2)
    assert r["best"] == pytest.approx(120 / 99 - 1) and r["worst"] == pytest.approx(-0.1)
    assert res["drawdown"]["max_drawdown"] == pytest.approx(-0.1)
    assert res["drawdown"]["peak_date"] == "2001-01-01" and res["drawdown"]["recovery_date"] == "2003-01-01"
    assert [p["value"] for p in res["moving_averages"]["2"]] == [105, 104.5, 109.5]
    vals = np.array([0.1, -0.1, 120 / 99 - 1])
    assert r["volatility_annualized"] == pytest.approx(vals.std(ddof=1))


def test_missing_values_are_not_interpolated():
    res = analytics.analyze(series_input([100, None, 121], "A"), [])
    assert res["summary"]["missing"] == 1 and res["returns"]["count"] == 1
    assert res["returns"]["mean_per_period"] == pytest.approx(0.21)
    assert any("non interpolate" in w for w in res["warnings"])


def test_rates_use_absolute_changes_and_negative_values():
    res = analytics.analyze(series_input([-0.5, -0.4, 0.5, 2.0], "A"), [], level_metrics=False)
    assert "returns" not in res and res["changes"]["count"] == 3
    with pytest.raises(analytics.AnalysisError):
        analytics.returns(analytics.to_pandas([("2020-01-01", -1.0), ("2021-01-01", 1.0)]), "log")


def test_anomaly_detection():
    vals = [100 + i for i in range(30)]
    vals[15] = 1000
    res = analytics.analyze(series_input(vals, "A", start=1950), [])
    assert res["anomalies"] and any("anomale" in w for w in res["warnings"])


def test_adf_on_random_walk_vs_white_noise():
    rng = np.random.default_rng(0)
    noise = analytics.analyze(series_input(list(100 + rng.normal(0, 1, 200)), "M", start=1990), [])
    walk = analytics.analyze(series_input(list(100 + np.cumsum(rng.normal(0, 1, 200))), "M", start=1990), [])
    assert noise["timeseries"]["adf"]["p_value"] < 0.05
    assert walk["timeseries"]["adf"]["p_value"] > 0.05


def test_compare_refuses_mixed_frequencies_without_explicit_procedure():
    m = series_input([float(i) for i in range(1, 37)], "M", 2000, sid=1)
    a = series_input([1.0, 2.0, 4.0], "A", 2000, sid=2)
    with pytest.raises(analytics.AnalysisError, match="frequenze diverse"):
        analytics.compare([m, a], None, "last", "levels")
    with pytest.raises(analytics.AnalysisError, match="non consentito"):
        analytics.compare([m, a], "M", "last", "levels")
    res = analytics.compare([m, a], "A", "last", "levels")
    assert res["frequency"] == "A" and res["common_observations"] == 3
    assert "metodo 'last'" in res["procedure"][0]
    assert [p["value"] for p in res["aligned"]["1"]] == [12.0, 24.0, 36.0]


def test_correlation_of_returns():
    x = series_input([100, 110, 99, 120, 130], "A", sid=1)
    y = series_input([50, 55, 49.5, 60, 65], "A", sid=2)
    res = analytics.compare([x, y], None, "last", "returns")
    assert res["correlation"]["1"]["2"] == pytest.approx(1.0)


# --- API ---------------------------------------------------------------------------------


@pytest.fixture
def wb_mock(monkeypatch):
    from nexus.services import finance as svc

    real = svc._fetcher
    monkeypatch.setattr(svc, "_fetcher", lambda settings: connectors.HttpFetcher(
        connectors.Cache(settings.cache_dir, 24), client=httpx.Client(transport=httpx.MockTransport(wb_handler))))
    yield
    svc._fetcher = real


def test_import_series_api(client, wb_mock):
    r = client.post("/api/finance/series/import", json={"connector": "world-bank", "indicator": "FP.CPI.TOTL.ZG", "country": "ITA", "category": "inflation"})
    assert r.status_code == 201, r.text
    s = r.json()
    # 2022 era vuoto ai margini della copertura: rimosso, non conteggiato come mancante.
    assert s["observation_count"] == 2 and s["missing_count"] == 0 and s["start_date"] == "2023-01-01"
    assert s["last_value"] == 0.98 and s["source_last_updated"] == "2026-10-08" and s["license_note"]
    assert client.post("/api/finance/series/import", json={"connector": "world-bank", "indicator": "FP.CPI.TOTL.ZG", "country": "ITA"}).status_code == 422
    a = client.get(f"/api/finance/series/{s['id']}/analysis").json()
    assert a["metrics_basis"] == "rates" and a["source"]["unit"] == "annual %"
    d = client.get("/api/dashboard").json()["indicators"]
    assert d["available"] and "tempo reale" in d["note"]
    assert client.get("/api/history/timeline?as_of_year=2023").json()["indicators"][0]["last_value"] == 5.6


def test_import_validation_and_missing_key(client):
    assert client.post("/api/finance/series/import", json={"connector": "world-bank", "indicator": "X"}).status_code == 422
    r = client.post("/api/finance/series/import", json={"connector": "fred", "series_id": "UNRATE"})
    assert r.status_code == 422 and "chiave" in r.json()["error"]["message"]


def test_csv_upload_and_compare(client):
    csv1 = "anno,valore\n2018,1\n2019,2\n2020,3\n2021,5\n2022,8\n"
    csv2 = "anno,valore\n2018,10\n2019,20\n2020,30\n2021,50\n2022,80\n"
    ids = []
    for name, c in (("A", csv1), ("B", csv2)):
        r = client.post("/api/finance/series/upload", files={"file": ("s.csv", c.encode())}, data={"name": name, "source_label": "Calcolo personale", "category": "indices"})
        assert r.status_code == 201, r.text
        ids.append(r.json()["id"])
    assert client.post("/api/finance/series/upload", files={"file": ("s.csv", csv1.encode())}, data={"name": "x", "source_label": " "}).status_code == 422
    cmp = client.post("/api/finance/compare", json={"series_ids": ids}).json()
    assert cmp["correlation"][str(ids[0])][str(ids[1])] == pytest.approx(1.0)
    an = client.get(f"/api/finance/series/{ids[0]}/analysis?ma=2&returns=log").json()
    assert an["metrics_basis"] == "levels" and an["returns"]["kind"] == "log"
    assert client.get(f"/api/finance/series/{ids[0]}/analysis?ma=1").status_code == 422
    assert client.post(f"/api/finance/series/{ids[0]}/refresh").status_code == 422
    assert client.delete(f"/api/finance/series/{ids[0]}").status_code == 409


def test_credentials_are_encrypted_and_masked(client, db):
    from nexus.models import Credential

    r = client.put("/api/credentials", json={"provider": "fred", "secret": "abcdef1234567890"})
    assert r.status_code == 200 and r.json()["hint"] == "…7890" and "abcdef" not in r.text
    stored = db.query(Credential).one()
    assert "abcdef1234567890" not in stored.secret_encrypted
    listed = client.get("/api/credentials").json()
    assert next(c for c in listed if c["provider"] == "fred")["configured"] is True
    assert "abcdef" not in json.dumps(listed)
    assert client.put("/api/credentials", json={"provider": "anthropic", "secret": ""}).status_code == 422
    assert client.delete("/api/credentials/fred").status_code == 204


def test_constant_growth_correlation_is_reported_as_undefined():
    x = series_input([1, 2, 4, 8, 16], "A", sid=1)
    y = series_input([3, 6, 12, 24, 48], "A", sid=2)
    res = analytics.compare([x, y], None, "last", "returns")
    assert res["correlation"]["1"]["2"] is None  # varianza nulla: non un numero inventato
