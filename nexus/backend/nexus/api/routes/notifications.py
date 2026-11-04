from fastapi import APIRouter

from ...services import notifications as svc
from ..deps import DB, CurrentUser
from ..schemas import NotificationOut

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
def list_notifications(db: DB, user: CurrentUser, unread_only: bool = False):
    return svc.list_for_user(db, user, unread_only=unread_only)


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: int, db: DB, user: CurrentUser):
    return svc.mark_read(db, user, notification_id)


@router.post("/read-all", summary="Segna tutte le notifiche come lette")
def mark_all_read(db: DB, user: CurrentUser) -> dict:
    return {"updated": svc.mark_all_read(db, user)}
