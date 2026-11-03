from fastapi import APIRouter

from ...core.errors import NotFoundError
from ...core.modules import MODULES, MODULES_BY_ID
from ..schemas import ModuleOut

router = APIRouter(prefix="/modules", tags=["modules"])


@router.get("", response_model=list[ModuleOut], summary="Le otto aree di NEXUS e il loro stato reale")
def list_modules() -> list[ModuleOut]:
    return [ModuleOut(**m.__dict__) for m in MODULES]


@router.get("/{module_id}", response_model=ModuleOut)
def get_module(module_id: str) -> ModuleOut:
    m = MODULES_BY_ID.get(module_id)
    if m is None:
        raise NotFoundError("Modulo non trovato.")
    return ModuleOut(**m.__dict__)
