import secrets
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import Guest


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_or_create_guest(
    db: Session = Depends(get_db),
    x_guest_session: str | None = Header(default=None),
):
    if x_guest_session:
        guest = db.execute(
            select(Guest).where(Guest.session_id == x_guest_session)
        ).scalar_one_or_none()

        if not guest:
            raise HTTPException(status_code=401, detail="Invalid guest session")

        return guest

    session_id = secrets.token_urlsafe(24)
    guest = Guest(session_id=session_id)

    db.add(guest)
    db.commit()
    db.refresh(guest)

    return guest
