from fastapi import APIRouter, status

from ...services import lab as svc
from ..deps import DB, CurrentUser
from ..schemas_lab import (
    BacktestIn, BootstrapIn, DebtIn, GBMIn, InflationIn, RegressionIn, SensitivityIn, SimulationOut, SimulationSummary, TaylorIn,
)

router = APIRouter(prefix="/lab", tags=["economic-lab"])


def _route(kind: str, model, summary: str):
    def handler(data: model, db: DB, user: CurrentUser):  # type: ignore[valid-type]
        return svc.run(db, user, kind, data)

    router.add_api_route(f"/simulations/{kind}", handler, methods=["POST"], response_model=SimulationOut,
                         status_code=status.HTTP_201_CREATED, summary=summary, name=f"run_{kind}")


_route("monte_carlo", GBMIn, "Monte Carlo (moto browniano geometrico)")
_route("monte_carlo_bootstrap", BootstrapIn, "Monte Carlo bootstrap su rendimenti storici di una serie")
_route("debt", DebtIn, "Dinamica del debito pubblico, shock sui tassi, crisi, incertezza")
_route("sensitivity", SensitivityIn, "Sensitività one-at-a-time del debito")
_route("inflation", InflationIn, "Scenari di inflazione")
_route("monetary_policy", TaylorIn, "Confronto tra regole di politica monetaria")
_route("regression", RegressionIn, "Regressione OLS tra serie")
_route("backtest", BacktestIn, "Backtest senza look-ahead")


@router.get("/simulations", response_model=list[SimulationSummary])
def list_simulations(db: DB, user: CurrentUser, kind: str | None = None):
    return svc.list_runs(db, user, kind)


@router.get("/simulations/{sim_id}", response_model=SimulationOut)
def get_simulation(sim_id: int, db: DB, user: CurrentUser):
    return svc.get(db, user, sim_id)


@router.delete("/simulations/{sim_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_simulation(sim_id: int, db: DB, user: CurrentUser, confirm: bool = False) -> None:
    svc.delete(db, user, sim_id, confirm)
