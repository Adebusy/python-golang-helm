from typing import Optional

from pydantic import BaseModel


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_at: str


class FileResponse(BaseModel):
    id: int
    original_filename: str
    stored_filename: str
    content_type: Optional[str]
    size_bytes: int
    uploaded_at: str


class DeleteResponse(BaseModel):
    message: str
    file_id: int
