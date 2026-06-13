from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from auth.dependencies import get_current_user
from db.database import async_session
from db.models import Document
import aiofiles
import os
import uuid

router = APIRouter()
UPLOAD_DIR = "/app/storage/documents"

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(async_session)
):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1]
    save_path = os.path.join(UPLOAD_DIR, f"{file_id}{ext}")

    async with aiofiles.open(save_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)

    doc = Document(
        user_id=user["user_id"],
        title=file.filename,
        file_path=save_path,
        content_type=file.content_type,
        status="pending"
    )
    db.add(doc)
    await db.commit()
    return {"id": doc.id, "status": doc.status}