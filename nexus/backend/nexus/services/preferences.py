from __future__ import annotations

from sqlalchemy.orm import Session

from ..api.schemas import ALL_WIDGETS, DashboardLayout
from ..core.errors import ValidationFailedError
from ..models import User, UserPreference
from . import activity

DASHBOARD_KEY = "dashboard.layout"


def get_dashboard_layout(db: Session, user: User) -> DashboardLayout:
    pref = db.get(UserPreference, (user.id, DASHBOARD_KEY))
    if pref is None:
        return DashboardLayout()
    try:
        layout = DashboardLayout.model_validate(pref.value)
    except ValueError:
        return DashboardLayout()
    return _normalize(layout)


def _normalize(layout: DashboardLayout) -> DashboardLayout:
    # Aggiunge in coda eventuali widget introdotti dopo il salvataggio.
    order = list(dict.fromkeys(layout.order))
    order += [w for w in ALL_WIDGETS if w not in order]
    return DashboardLayout(order=order, hidden=list(dict.fromkeys(layout.hidden)))


def set_dashboard_layout(db: Session, user: User, layout: DashboardLayout) -> DashboardLayout:
    if len(set(layout.order)) != len(layout.order):
        raise ValidationFailedError("L'ordine dei widget contiene duplicati.")
    layout = _normalize(layout)
    pref = db.get(UserPreference, (user.id, DASHBOARD_KEY))
    if pref is None:
        pref = UserPreference(user_id=user.id, key=DASHBOARD_KEY, value=layout.model_dump())
        db.add(pref)
    else:
        pref.value = layout.model_dump()
    activity.record(
        db, user=user, actor="user", action="dashboard.layout", summary="Aggiornato il layout della dashboard"
    )
    db.commit()
    return layout
