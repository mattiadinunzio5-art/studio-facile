from fastapi import APIRouter, status

from ...services import credentials as svc
from ..deps import DB, AppSettings, CurrentUser
from ..schemas_finance import CredentialIn, CredentialOut

router = APIRouter(prefix="/credentials", tags=["credentials"])


@router.get("", response_model=list[CredentialOut], summary="Credenziali configurate (mai restituite in chiaro)")
def list_credentials(db: DB, user: CurrentUser):
    return svc.list_credentials(db, user)


@router.put("", response_model=CredentialOut)
def set_credential(data: CredentialIn, db: DB, user: CurrentUser, settings: AppSettings):
    return svc.set_credential(db, user, settings, data)


@router.delete("/{provider}", status_code=status.HTTP_204_NO_CONTENT)
def delete_credential(provider: str, db: DB, user: CurrentUser) -> None:
    svc.delete_credential(db, user, provider)
