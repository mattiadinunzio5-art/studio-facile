"""Schemi API — Economic Laboratory (Fase 6). Limiti espliciti su ogni parametro."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .schemas import ORMModel, UTCDateTime

Rate = Field(ge=-0.5, le=2.0)


class GBMIn(BaseModel):
    s0: float = Field(gt=0, le=1e12)
    mu: float = Field(ge=-1, le=1)
    sigma: float = Field(ge=0, le=3)
    years: float = Field(gt=0, le=50)
    steps_per_year: int = Field(default=12, ge=1, le=252)
    n_paths: int = Field(default=2000, ge=100, le=20000)
    seed: int = Field(default=42, ge=0, le=2**31)
    threshold: float | None = None
    title: str | None = None


class BootstrapIn(BaseModel):
    series_id: int
    years: float = Field(gt=0, le=30)
    n_paths: int = Field(default=2000, ge=100, le=10000)
    block: int = Field(default=6, ge=1, le=60)
    seed: int = Field(default=42, ge=0, le=2**31)


class CrisisIn(BaseModel):
    start: int = Field(ge=1, le=100)
    years: int = Field(ge=1, le=20)
    g_shock: float = Field(default=0.0, ge=-0.5, le=0.5)
    r_shock: float = Field(default=0.0, ge=-0.2, le=0.5)
    pb_shock: float = Field(default=0.0, ge=-30, le=30)


class StochasticIn(BaseModel):
    n_paths: int = Field(default=2000, ge=100, le=10000)
    sd_r: float = Field(default=0.01, ge=0, le=0.2)
    sd_g: float = Field(default=0.02, ge=0, le=0.3)
    corr: float = Field(default=0.0, ge=-1, le=1)


class DebtIn(BaseModel):
    d0: float = Field(ge=0, le=1000, description="Debito iniziale, % PIL")
    r_eff0: float = Rate
    r_market: float = Rate
    avg_maturity: float = Field(default=7.0, gt=0, le=50)
    g: float = Rate
    pb: float = Field(default=0.0, ge=-30, le=30, description="Saldo primario, % PIL")
    years: int = Field(default=10, ge=1, le=100)
    rate_shock: float = Field(default=0.0, ge=-0.2, le=0.5)
    shock_start: int = Field(default=1, ge=1, le=100)
    crisis: CrisisIn | None = None
    stochastic: StochasticIn | None = None
    seed: int = Field(default=42, ge=0, le=2**31)
    counterfactual: bool = False
    title: str | None = None


class SensitivityIn(BaseModel):
    base: DebtIn
    ranges: dict[Literal["d0", "r_eff0", "r_market", "avg_maturity", "g", "pb"], tuple[float, float]] = Field(min_length=1)


class InflationIn(BaseModel):
    amount: float = Field(gt=0, le=1e12)
    nominal_rate: float = Rate
    years: int = Field(ge=1, le=100)
    inflation_levels: list[float] = Field(min_length=1, max_length=8)


class TaylorRuleIn(BaseModel):
    name: str = Field(max_length=60)
    a: float = Field(ge=-3, le=5)
    b: float = Field(ge=-3, le=5)
    floor: float | None = Field(default=None, ge=-0.1, le=0.2)


class TaylorIn(BaseModel):
    labels: list[str] = Field(min_length=1, max_length=400)
    inflation: list[float] = Field(min_length=1, max_length=400)
    output_gap: list[float] = Field(min_length=1, max_length=400)
    actual_rate: list[float] | None = None
    rules: list[TaylorRuleIn] = Field(min_length=1, max_length=6)
    r_star: float = Field(default=0.02, ge=-0.05, le=0.1)
    pi_target: float = Field(default=0.02, ge=-0.05, le=0.2)


class RegressionIn(BaseModel):
    y_series_id: int
    x_series_ids: list[int] = Field(min_length=1, max_length=5)
    transform: Literal["levels", "diff", "pct"] = "diff"
    lags: int = Field(default=0, ge=0, le=12)
    target_frequency: Literal["D", "W", "M", "Q", "A"] | None = None
    method: Literal["last", "mean", "sum"] = "mean"


class BacktestIn(BaseModel):
    series_id: int
    strategy: Literal["buy_hold", "ma_cross", "momentum"]
    fast: int = Field(default=10, ge=1, le=500)
    slow: int = Field(default=50, ge=2, le=1000)
    lookback: int = Field(default=12, ge=1, le=500)
    cost_bps: float = Field(default=10, ge=0, le=500)
    rf: float = Field(default=0.0, ge=-0.05, le=0.3)


class SimulationOut(ORMModel):
    id: int
    kind: str
    title: str
    params: dict
    result: dict
    counterfactual: bool
    created_at: UTCDateTime


class SimulationSummary(ORMModel):
    id: int
    kind: str
    title: str
    counterfactual: bool
    created_at: UTCDateTime
