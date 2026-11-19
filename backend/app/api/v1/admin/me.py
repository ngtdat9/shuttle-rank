"""Current admin session."""

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import AdminPrincipal, require_admin

router = APIRouter()


class AdminMeResponse(BaseModel):
    id: str
    email: str | None
    display_name: str | None
    auth_mode: Literal["supabase", "dev"]


@router.get("/me", response_model=AdminMeResponse)
def read_admin_me(principal: AdminPrincipal = Depends(require_admin)) -> AdminMeResponse:
    return AdminMeResponse(
        id=principal.id,
        email=principal.email,
        display_name=principal.display_name,
        auth_mode=principal.auth_mode,
    )
