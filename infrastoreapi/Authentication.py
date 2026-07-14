
from datetime import datetime, timedelta, timezone

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from pathlib import Path
from typing import Generator
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import sqlite3
import secrets
import os
 
security = HTTPBearer()


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "files.db"

TOKEN_EXPIRY_MINUTES = int(os.getenv("TOKEN_EXPIRY_MINUTES", "60"))

def get_database_connection():
    connection = sqlite3.connect(
        DATABASE_PATH,
        check_same_thread=False,
    )

    connection.row_factory = sqlite3.Row

    try:
        yield connection
    finally:
        connection.close()

def generate_access_token() -> tuple[str, datetime]:
    token = secrets.token_urlsafe(48)
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=TOKEN_EXPIRY_MINUTES
    )

    return token, expires_at

def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    connection: sqlite3.Connection = Depends(get_database_connection),
) -> str:
    token = credentials.credentials

    token_record = connection.execute(
        """
        SELECT token, expires_at
        FROM access_tokens
        WHERE token = ?
        """,
        (token,),
    ).fetchone()

    if token_record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expires_at = datetime.fromisoformat(token_record["expires_at"])

    if datetime.now(timezone.utc) >= expires_at:
        connection.execute(
            "DELETE FROM access_tokens WHERE token = ?",
            (token,),
        )
        connection.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token