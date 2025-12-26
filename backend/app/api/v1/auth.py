from fastapi import APIRouter, Depends

from app.deps.auth import get_or_create_guest
from app.schemas import GuestSessionResponse
from app.models import Guest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/guest", response_model=GuestSessionResponse)
def create_guest_session(
    guest: Guest = Depends(get_or_create_guest),
):
    return GuestSessionResponse(session_id=guest.session_id)
