import math

import numpy as np
import pandas as pd
import pytest

from nexus.simulations import models as M


def test_gbm_matches_analytic_mean_and_is_reproducible():
    r = M.monte_carlo_gbm(100, 0.05, 0.2, 5, 12, 20000, 1)
    assert r.results["final"]["mean"] == pytest.approx(r.results["final"]["analytic_mean"], rel=0.02)
    again = M.monte_carlo_gbm(100, 0.05, 0.2, 5, 12, 20000, 1)
    assert again.results["final"] == r.results["final"]
    det = M.monte_carlo_gbm(100, 0.05, 0.0, 2, 4, 100, 1)
    assert det.results["final"]["p5"] == pytest.approx(100 * math.exp(0.1), abs=1e-5)
    fan = r.results["fan"]
    assert len(fan) == 61 and all(f["p5"] <= f["p50"] <= f["p95"] for f in fan)
    d = r.to_dict()
    assert d["label"].startswith("Simulazione basata su ipotesi") and d["hypotheses"] and d["limitations"] and d["method"]


def test_bootstrap_requires_enough_positive_data():
    with pytest.raises(M.SimulationError):
        M.monte_carlo_bootstrap("x", ["2020"] * 5, [1, 2, 3, 4, 5], 12, 1, 100, 3, 0)
    vals = list(100 * np.exp(np.cumsum(np.random.default_rng(0).normal(0.005, 0.03, 60))))
    r = M.monte_carlo_bootstrap("x", [f"d{i}" for i in range(60)], vals, 12, 2, 500, 6, 0)
    assert r.results["final"]["start"] == pytest.approx(vals[-1]) and r.results["historical"]["n_returns"] == 59


def test_debt_equation_known_values():
    assert M.debt_path(100, [0.04], [0.02], [0.0])[1] == pytest.approx(100 * 1.04 / 1.02)
    flat = M.debt_dynamics(100, 0.03, 0.03, 7, 0.03, 0.0, 10)
    assert flat.results["baseline"]["debt"][-1] == pytest.approx(100)
    # Il saldo primario stabilizzante mantiene il debito costante.
    base = M.debt_dynamics(130, 0.04, 0.04, 7, 0.02, 0.0, 10)
    pb = base.results["debt_stabilizing_primary_balance"]
    stab = M.debt_dynamics(130, 0.04, 0.04, 7, 0.02, pb, 10)
    assert stab.results["baseline"]["debt"][-1] == pytest.approx(130, abs=1e-3)


def test_rate_shock_passes_through_gradually():
    r = M.debt_dynamics(140, 0.03, 0.03, 8, 0.03, 0.0, 10, rate_shock=0.02)
    eff = r.results["rate_shock"]["effective_rate"]
    assert eff[0] == pytest.approx(0.03 + 0.02 / 8)
    assert eff[-1] < 0.05 and r.results["rate_shock_delta_final"] > 0


def test_crisis_and_stochastic_paths():
    r = M.debt_dynamics(100, 0.03, 0.03, 7, 0.03, 0.0, 10, crisis={"start": 2, "years": 2, "g_shock": -0.08, "r_shock": 0.01},
                        stochastic={"n_paths": 500, "sd_r": 0.005, "sd_g": 0.02, "corr": -0.3}, seed=3, counterfactual=True)
    assert r.results["crisis"]["debt"][-1] > r.results["baseline"]["debt"][-1]
    assert len(r.results["fan"]) == 11 and 0 <= r.results["prob_final_above_start"] <= 1
    assert r.to_dict()["label"].startswith("Scenario ipotetico (controfattuale)")


def test_sensitivity_tornado_sorted():
    base = {"d0": 120, "r_eff0": 0.03, "r_market": 0.03, "avg_maturity": 7, "g": 0.03, "pb": 0.0, "years": 10}
    r = M.sensitivity(base, {"g": (0.0, 0.05), "pb": (-1, 1)})
    swings = [x["swing"] for x in r.results["tornado"]]
    assert swings == sorted(swings, reverse=True)
    with pytest.raises(M.SimulationError):
        M.sensitivity(base, {"years": (5, 10)})


def test_inflation_fisher_and_rule_of_72():
    r = M.inflation_scenarios(1000, 0.03, 10, [0.02, 0.072])
    s = {x["inflation"]: x for x in r.results["summary"]}
    assert s[0.02]["real_rate"] == pytest.approx(1.03 / 1.02 - 1, abs=1e-6)
    assert s[0.072]["halving_years"] == pytest.approx(10.0, abs=0.1)
    assert s[0.02]["purchasing_power_end"] == pytest.approx(1000 / 1.02**10, abs=0.01)


def test_taylor_rule_classic_values():
    r = M.taylor_rules([0.04], [0.01], ["2000"], [{"name": "Taylor 1993", "a": 0.5, "b": 0.5}, {"name": "floor", "a": 0.5, "b": 0.5, "floor": 0.1}],
                       r_star=0.02, pi_target=0.02, actual_rate=[0.06])
    assert r.results["prescribed"]["Taylor 1993"][0] == pytest.approx(0.075)
    assert r.results["prescribed"]["floor"][0] == pytest.approx(0.1)
    assert r.results["gap_vs_actual"]["Taylor 1993"][0] == pytest.approx(0.015)
    assert r.counterfactual is True
    with pytest.raises(M.SimulationError):
        M.taylor_rules([0.01, 0.02], [0.0], ["a"], [{"a": 1, "b": 1}], 0.02, 0.02)


def test_regression_recovers_coefficient_and_flags_spurious_levels():
    rng = np.random.default_rng(1)
    idx = pd.date_range("2000-01-01", periods=120, freq="MS")
    x = pd.Series(np.cumsum(rng.normal(0, 1, 120)), index=idx)
    y = 2 * x + rng.normal(0, 0.1, 120)
    r = M.regression("y", y, {"x": x}, "diff", 0, [], [])
    coef = next(c for c in r.results["coefficients"] if c["name"] == "x")
    assert coef["coef"] == pytest.approx(2, abs=0.05) and coef["p_value"] < 0.001 and r.results["n"] == 119
    walk_a = pd.Series(np.cumsum(rng.normal(0, 1, 120)), index=idx)
    walk_b = pd.Series(np.cumsum(rng.normal(0, 1, 120)), index=idx)
    spurious = M.regression("a", walk_a, {"b": walk_b}, "levels", 0, [], [])
    assert any("spuria" in w for w in spurious.warnings)


def _prices(n=200, seed=0):
    rng = np.random.default_rng(seed)
    p = 100 * np.exp(np.cumsum(rng.normal(0.0005, 0.01, n)))
    return [d.strftime("%Y-%m-%d") for d in pd.bdate_range("2015-01-01", periods=n)], list(p)


@pytest.mark.parametrize("strategy,params", [("ma_cross", {"fast": 5, "slow": 20}), ("momentum", {"lookback": 10})])
def test_backtest_has_no_look_ahead(strategy, params):
    dates, prices = _prices()
    k = 120
    altered = prices[:k] + [x * (3 if i % 2 else 0.3) for i, x in enumerate(prices[k:])]
    a = M.backtest("x", dates, prices, 252, strategy, params, 0, 0.0)
    b = M.backtest("x", dates, altered, 252, strategy, params, 0, 0.0)
    eq_a = {e["date"]: e["strategy"] for e in a.results["equity"]}
    eq_b = {e["date"]: e["strategy"] for e in b.results["equity"]}
    past = [d for d in eq_a if d < dates[k]]
    assert past and all(eq_a[d] == eq_b[d] for d in past)


def test_backtest_costs_and_bias_disclosures():
    dates, prices = _prices()
    free = M.backtest("x", dates, prices, 252, "ma_cross", {"fast": 5, "slow": 20}, 0, 0.0)
    costly = M.backtest("x", dates, prices, 252, "ma_cross", {"fast": 5, "slow": 20}, 50, 0.0)
    assert costly.results["strategy"]["total_return"] < free.results["strategy"]["total_return"]
    assert any("sopravvivenza" in w for w in free.warnings) and any("point-in-time" in w for w in free.warnings)
    bh = M.backtest("x", dates, prices, 252, "buy_hold", {}, 0, 0.0)
    # Buy & hold entra dal secondo periodo (segnale applicato al periodo successivo).
    assert bh.results["strategy"]["total_return"] == pytest.approx(prices[-1] / prices[0] - 1, abs=1e-5)
    with pytest.raises(M.SimulationError):
        M.backtest("x", dates, prices, 252, "ma_cross", {"fast": 30, "slow": 20}, 0, 0)


# --- API ---------------------------------------------------------------------------------


def test_lab_api_roundtrip_and_validation(client):
    r = client.post("/api/lab/simulations/monte_carlo", json={"s0": 100, "mu": 0.05, "sigma": 0.2, "years": 1, "n_paths": 500})
    assert r.status_code == 201 and r.json()["result"]["method"]
    assert client.post("/api/lab/simulations/monte_carlo", json={"s0": 100, "mu": 0.05, "sigma": 0.2, "years": 1, "n_paths": 50000}).status_code == 422
    d = client.post("/api/lab/simulations/debt", json={"d0": 135, "r_eff0": 0.03, "r_market": 0.04, "g": 0.03, "pb": 1, "years": 10, "rate_shock": 0.01, "counterfactual": True}).json()
    assert d["counterfactual"] and "rate_shock" in d["result"]["results"]
    t = client.post("/api/lab/simulations/monetary_policy", json={"labels": ["a"], "inflation": [0.03], "output_gap": [0], "rules": [{"name": "T", "a": 0.5, "b": 0.5}]}).json()
    assert t["counterfactual"] is True
    assert client.post("/api/lab/simulations/sensitivity", json={"base": {"d0": 100, "r_eff0": 0.03, "r_market": 0.03, "g": 0.03}, "ranges": {"g": [0.05, 0.01]}}).status_code == 422
    assert len(client.get("/api/lab/simulations").json()) == 3
    sid = r.json()["id"]
    assert client.delete(f"/api/lab/simulations/{sid}").status_code == 409
    assert client.delete(f"/api/lab/simulations/{sid}?confirm=true").status_code == 204
    assert client.post("/api/lab/simulations/unknown", json={}).status_code in (404, 405)


def test_lab_with_series(client):
    dates, prices = _prices(80)
    csv = "data,valore\n" + "\n".join(f"{d},{p}" for d, p in zip(dates, prices))
    sid = client.post("/api/finance/series/upload", files={"file": ("p.csv", csv.encode())}, data={"name": "Indice test", "source_label": "Simulato per test", "category": "indices"}).json()["id"]
    bt = client.post("/api/lab/simulations/backtest", json={"series_id": sid, "strategy": "ma_cross", "fast": 5, "slow": 20})
    assert bt.status_code == 201 and "Simulato per test" in " ".join(bt.json()["result"]["data_used"])
    bs = client.post("/api/lab/simulations/monte_carlo_bootstrap", json={"series_id": sid, "years": 0.5, "n_paths": 200})
    assert bs.status_code == 201
    annual = client.post("/api/finance/series/upload", files={"file": ("a.csv", b"anno,v\n2015,1\n2016,2\n2017,3\n")}, data={"name": "A", "source_label": "t"}).json()["id"]
    r = client.post("/api/lab/simulations/regression", json={"y_series_id": sid, "x_series_ids": [annual]})
    assert r.status_code == 422 and "Frequenze diverse" in r.json()["error"]["message"]
    assert client.post("/api/lab/simulations/regression", json={"y_series_id": sid, "x_series_ids": [sid]}).status_code == 422
