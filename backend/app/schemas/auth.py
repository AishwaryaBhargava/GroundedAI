from pydantic import BaseModel


class GuestSessionResponse(BaseModel):
    session_id: str
