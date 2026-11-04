from typing import Annotated

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel, Field, StringConstraints

from ...billing import PaymentNotConfigured, get_provider
from ...core import plans
from ...core.errors import NexusError
from ...services import admin as admin_svc
from ...services import auth as svc
from ..deps import DB, AdminUser, AppSettings, CurrentUser, request_token
from ..schemas import CleanStr, UserOut

router = APIRouter(tags=["account"])

Email = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")]


class RegisterIn(BaseModel):
    email: Email
    password: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    display_name: Annotated[CleanStr, StringConstraints(max_length=120)] = ""


class LoginIn(BaseModel):
    email: Email
    password: Annotated[str, StringConstraints(min_length=1, max_length=200)]


class PasswordIn(BaseModel):
    current: Annotated[str, StringConstraints(max_length=200)]
    new: Annotated[str, StringConstraints(min_length=1, max_length=200)]


class ProfileIn(BaseModel):
    display_name: Annotated[CleanStr, StringConstraints(min_length=1, max_length=120)]


class AdminUserUpdate(BaseModel):
    role: Annotated[str, StringConstraints(pattern=r"^(admin|user)$")] | None = None
    plan: Annotated[str, StringConstraints(pattern=r"^(free|premium)$")] | None = None
    is_active: bool | None = None


class PaymentNotAvailable(NexusError):
    status_code = 501
    code = "payments_not_configured"


def _set_cookie(response: Response, token: str, settings) -> None:
    response.set_cookie(svc.COOKIE_NAME, token, max_age=settings.session_hours * 3600, httponly=True, samesite="strict",
                        secure=settings.cookie_secure, path="/api")


@router.get("/auth/config", summary="Modalità di autenticazione")
def auth_config(settings: AppSettings) -> dict:
    return {"mode": settings.auth_mode, "allow_registration": settings.allow_registration and settings.auth_mode == "multi"}


@router.post("/auth/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(data: RegisterIn, request: Request, response: Response, db: DB, settings: AppSettings):
    u = svc.register(db, settings, data.email, data.password, data.display_name)
    _, token = svc.login(db, settings, data.email, data.password, request.headers.get("user-agent", ""), request.client.host if request.client else "")
    _set_cookie(response, token, settings)
    return u


@router.post("/auth/login", response_model=UserOut)
def login(data: LoginIn, request: Request, response: Response, db: DB, settings: AppSettings):
    u, token = svc.login(db, settings, data.email, data.password, request.headers.get("user-agent", ""), request.client.host if request.client else "")
    _set_cookie(response, token, settings)
    return u


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: DB) -> None:
    svc.logout(db, request_token(request))
    response.delete_cookie(svc.COOKIE_NAME, path="/api")


@router.get("/auth/sessions")
def sessions(request: Request, db: DB, user: CurrentUser) -> list[dict]:
    current = getattr(request.state, "session_id", None)
    return [{"id": s.id, "created_at": s.created_at.isoformat(), "last_seen_at": s.last_seen_at.isoformat() if s.last_seen_at else None,
             "user_agent": s.user_agent, "ip": s.ip, "current": s.id == current} for s in svc.list_sessions(db, user)]


@router.delete("/auth/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke(session_id: int, db: DB, user: CurrentUser) -> None:
    svc.revoke_session(db, user, session_id)


@router.post("/auth/password", status_code=status.HTTP_204_NO_CONTENT, summary="Cambia password (chiude le altre sessioni)")
def change_password(data: PasswordIn, request: Request, db: DB, user: CurrentUser) -> None:
    svc.change_password(db, user, data.current, data.new, getattr(request.state, "session_id", None))


@router.patch("/me", response_model=UserOut)
def update_profile(data: ProfileIn, db: DB, user: CurrentUser):
    user.display_name = data.display_name
    db.commit()
    db.refresh(user)
    return user


@router.get("/me/usage", summary="Piano e utilizzo")
def my_usage(db: DB, user: CurrentUser) -> dict:
    return {"plan": plans.as_dict(plans.plan_of(user)), "usage": plans.usage(db, user)}


@router.get("/billing/plans")
def billing_plans() -> dict:
    return {"plans": [plans.as_dict(p) for p in plans.PLANS.values()], "payments_enabled": False,
            "note": "Nessun pagamento reale: il piano viene assegnato da un amministratore. È predisposta un'interfaccia per un futuro fornitore di pagamenti."}


@router.post("/billing/checkout/{plan_id}", summary="Pagamento (non attivo)")
def checkout(plan_id: str, user: CurrentUser) -> dict:
    try:
        return {"url": get_provider().create_checkout(user.id, plan_id)}
    except PaymentNotConfigured as exc:
        raise PaymentNotAvailable(str(exc)) from exc


@router.get("/admin/users", summary="Utenti (solo amministratori)")
def admin_users(db: DB, _: AdminUser) -> list[dict]:
    return admin_svc.list_users(db)


@router.patch("/admin/users/{user_id}")
def admin_update_user(user_id: int, data: AdminUserUpdate, db: DB, admin: AdminUser) -> dict:
    return admin_svc.update_user(db, admin, user_id, data.role, data.plan, data.is_active)


@router.get("/admin/stats")
def admin_stats(db: DB, _: AdminUser) -> dict:
    return admin_svc.stats(db)
