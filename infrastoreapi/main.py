import os
import secrets
import shutil
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import BaseModel

from models import TokenResponse, FileResponse, DeleteResponse
from Authentication import verify_token, generate_access_token, get_database_connection
# ---------------------------------------------------------
# Application configuration
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
DATABASE_PATH = BASE_DIR / "files.db"

# DJANGO_SUPERUSER_USERNAME=admin
# DJANGO_SUPERUSER_PASSWORD=secret123

# Set these as environment variables in production.
API_USERNAME = os.getenv("DJANGO_SUPERUSER_USERNAME")
API_PASSWORD = os.getenv("DJANGO_SUPERUSER_PASSWORD")

# API_USERNAME = 'admin'
# API_PASSWORD = 'secret123'

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
DATABASE_DIR = BASE_DIR / "db"

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "application/pdf",
    "text/plain",
    "application/zip",
    "application/octet-stream",
}

def initialise_database() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_filename TEXT NOT NULL,
                stored_filename TEXT NOT NULL UNIQUE,
                file_path TEXT NOT NULL,
                content_type TEXT,
                size_bytes INTEGER NOT NULL,
                uploaded_at TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS access_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
            """
        )

        connection.commit()


# ---------------------------------------------------------
# Application startup
# ---------------------------------------------------------

@asynccontextmanager
async def lifespan(application: FastAPI):
    initialise_database()
    yield


app = FastAPI(
    title="File Management API",
    description="Upload, list and delete files using bearer-token authentication.",
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------
# Root endpoint
# ---------------------------------------------------------

@app.get("/")
def root():
    return {
        "message": "File Management API is running.",
        "documentation": "/docs",
    }


# ---------------------------------------------------------
# Generate an authorization token
# ---------------------------------------------------------

@app.post("/api/token/", response_model=TokenResponse)
def get_token(
    DJANGO_SUPERUSER_USERNAME: str = Form(...),
    DJANGO_SUPERUSER_PASSWORD: str = Form(...),
    connection: sqlite3.Connection = Depends(get_database_connection),
):
    """
    Generate an authorization token.

    The returned token must be passed to protected endpoints as:

    Authorization: Bearer <access_token>
    """

    valid_username = secrets.compare_digest(DJANGO_SUPERUSER_USERNAME, API_USERNAME)
    valid_password = secrets.compare_digest(DJANGO_SUPERUSER_PASSWORD, API_PASSWORD)

    if not valid_username or not valid_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token, expires_at = generate_access_token()
    created_at = datetime.now(timezone.utc)

    connection.execute(
        """
        INSERT INTO access_tokens (
            token,
            created_at,
            expires_at
        )
        VALUES (?, ?, ?)
        """,
        (
            token,
            created_at.isoformat(),
            expires_at.isoformat(),
        ),
    )

    connection.commit()

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_at=expires_at.isoformat(),
    )


# ---------------------------------------------------------
# Upload and save a file
# ---------------------------------------------------------

@app.post("/upload", response_model=FileResponse, status_code=status.HTTP_201_CREATED,)
async def upload_file(
    uploaded_file: UploadFile = File(...),
    token : str = Depends(verify_token),
    connection: sqlite3.Connection = Depends(get_database_connection),
):
    """
    Save an uploaded file in the uploads folder and save its metadata
    in the SQLite database.
    """

    if not uploaded_file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file must have a filename.",
        )

    if (
        uploaded_file.content_type
        and uploaded_file.content_type not in ALLOWED_CONTENT_TYPES
    ):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type '{uploaded_file.content_type}' is not allowed.",
        )

    original_filename = Path(uploaded_file.filename).name
    file_extension = Path(original_filename).suffix.lower()

    stored_filename = f"{uuid4().hex}{file_extension}"
    destination_path = UPLOAD_DIR / stored_filename

    try:
        with destination_path.open("wb") as destination:
            shutil.copyfileobj(uploaded_file.file, destination)

        file_size = destination_path.stat().st_size

        if file_size == 0:
            destination_path.unlink(missing_ok=True)

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty files are not allowed.",
            )

        if file_size > MAX_FILE_SIZE:
            destination_path.unlink(missing_ok=True)

            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="The uploaded file exceeds the 20 MB size limit.",
            )

        uploaded_at = datetime.now(timezone.utc).isoformat()

        cursor = connection.execute(
            """
            INSERT INTO files (
                original_filename,
                stored_filename,
                file_path,
                content_type,
                size_bytes,
                uploaded_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                original_filename,
                stored_filename,
                str(destination_path),
                uploaded_file.content_type,
                file_size,
                uploaded_at,
            ),
        )

        connection.commit()

        return FileResponse(
            id=cursor.lastrowid,
            original_filename=original_filename,
            stored_filename=stored_filename,
            content_type=uploaded_file.content_type,
            size_bytes=file_size,
            uploaded_at=uploaded_at,
        )

    except HTTPException:
        raise

    except (OSError, sqlite3.DatabaseError) as error:
        destination_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error

    finally:
        await uploaded_file.close()


# ---------------------------------------------------------
# Get all uploaded files
# ---------------------------------------------------------

@app.get("/files/", response_model=list[FileResponse])
def get_all_files(
    _: str = Depends(verify_token),
    connection: sqlite3.Connection = Depends(get_database_connection),
):
    """
    Get the metadata of all files stored in the SQLite database.
    """

    records = connection.execute(
        """
        SELECT
            id,
            original_filename,
            stored_filename,
            content_type,
            size_bytes,
            uploaded_at
        FROM files
        ORDER BY id DESC
        """
    ).fetchall()

    return [
        FileResponse(
            id=record["id"],
            original_filename=record["original_filename"],
            stored_filename=record["stored_filename"],
            content_type=record["content_type"],
            size_bytes=record["size_bytes"],
            uploaded_at=record["uploaded_at"],
        )
        for record in records
    ]


# ---------------------------------------------------------
# Delete a file by its database ID
# ---------------------------------------------------------

@app.delete("/files/{file_id}", response_model=DeleteResponse)
def delete_file_by_file_id(
    file_id: int,
    _: str = Depends(verify_token),
    connection: sqlite3.Connection = Depends(get_database_connection),
):
    """
    Delete a file from the uploads folder and remove its database record.
    """

    record = connection.execute(
        """
        SELECT id, file_path
        FROM files
        WHERE id = ?
        """,
        (file_id,),
    ).fetchone()

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID {file_id} was not found.",
        )

    file_path = Path(record["file_path"])

    try:
        if file_path.exists():
            file_path.unlink()

        connection.execute(
            "DELETE FROM files WHERE id = ?",
            (file_id,),
        )

        connection.commit()

        return DeleteResponse(
            message="File and database record deleted successfully.",
            file_id=file_id,
        )

    except (OSError, sqlite3.DatabaseError) as error:
        connection.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The file could not be deleted.",
        ) from error
