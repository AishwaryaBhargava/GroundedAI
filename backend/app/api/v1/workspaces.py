from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.deps.auth import get_or_create_guest
from app.deps.db import get_db
from app.models import Workspace, Guest
from app.schemas import WorkspaceCreateRequest, WorkspaceResponse

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("", response_model=list[WorkspaceResponse])
def list_workspaces(
    db: Session = Depends(get_db),
    guest: Guest = Depends(get_or_create_guest),
):
    rows = db.execute(
        select(Workspace)
        .where(Workspace.owner_guest_id == guest.id)
        .order_by(Workspace.created_at.desc())
    ).scalars().all()

    return [
        WorkspaceResponse(id=w.id, name=w.name, is_guest=w.is_guest)
        for w in rows
    ]


@router.post("", response_model=WorkspaceResponse)
def create_workspace(
    payload: WorkspaceCreateRequest,
    db: Session = Depends(get_db),
    guest: Guest = Depends(get_or_create_guest),
):
    existing = db.execute(
        select(Workspace).where(Workspace.owner_guest_id == guest.id)
    ).scalars().all()

    if len(existing) >= 5:
        raise HTTPException(
            status_code=403,
            detail="Workspace limit reached (maximum 5 for guest accounts).",
        )

    name = (payload.name or "").strip() or "Guest Workspace"

    w = Workspace(
        owner_guest_id=guest.id,
        owner_user_id=None,
        name=name,
        is_guest=True,
    )
    db.add(w)
    db.commit()
    db.refresh(w)

    return WorkspaceResponse(id=w.id, name=w.name, is_guest=w.is_guest)
