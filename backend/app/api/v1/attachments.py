import mimetypes
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/attachments")

BASE_ATTACHMENT_DIR = Path(__file__).resolve().parents[2] / "storage" / "attachments"
BASE_ATTACHMENT_DIR.mkdir(parents=True, exist_ok=True)


def _safe_filename(filename: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", filename or "attachment")
    return cleaned.strip("_") or "attachment"


def _user_attachment_dir(user_id: uuid.UUID) -> Path:
    directory = BASE_ATTACHMENT_DIR / str(user_id)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


class AttachmentOut(BaseModel):
    id: uuid.UUID
    filename: str
    url: str
    size: int
    content_type: str | None = None


@router.post("", response_model=AttachmentOut)
async def upload_attachment(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    content = await file.read()
    if len(content) > 1_000_000:
        raise HTTPException(status_code=413, detail="File is too large. Attachments must be under 1MB.")

    user_dir = _user_attachment_dir(user.id)
    attachment_id = uuid.uuid4()
    filename = _safe_filename(file.filename or "attachment")
    destination = user_dir / f"{attachment_id}_{filename}"
    destination.write_bytes(content)

    return AttachmentOut(
        id=attachment_id,
        filename=file.filename or filename,
        url=f"/api/v1/attachments/{user.id}/{attachment_id}",
        size=len(content),
        content_type=file.content_type,
    )


@router.get("/{user_id}/{attachment_id}")
async def get_attachment(
    user_id: uuid.UUID,
    attachment_id: uuid.UUID,
    user: User = Depends(get_current_user),
):
    if str(user_id) != str(user.id):
        raise HTTPException(status_code=403, detail="Unable to access attachment.")

    user_dir = BASE_ATTACHMENT_DIR / str(user.id)
    if not user_dir.exists():
        raise HTTPException(status_code=404, detail="Attachment not found.")

    matches = list(user_dir.glob(f"{attachment_id}_*"))
    if not matches:
        raise HTTPException(status_code=404, detail="Attachment not found.")

    path = matches[0]
    content_type, _ = mimetypes.guess_type(path.name)
    return FileResponse(path, filename=path.name.split("_", 1)[1] if "_" in path.name else path.name, media_type=content_type or "application/octet-stream")
