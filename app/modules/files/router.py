from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.database import get_db_session
from app.api.dependencies.ownership import Principal, get_guest_or_member_principal
from app.modules.files.service import FileService


router = APIRouter(prefix="/files", tags=["files"])


@router.get(
    "/{fileId}",
    summary="Get private file",
    responses={200: {"content": {"application/octet-stream": {}}}},
)
async def get_file(
    fileId: UUID,
    principal: Principal = Depends(get_guest_or_member_principal),
    session: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    service = FileService(session)
    stored_file = await service.get_owned_file(file_id=fileId, principal=principal)
    return StreamingResponse(
        iter([stored_file.content]),
        media_type=stored_file.metadata.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{stored_file.metadata.original_name}"',
            "X-File-Id": str(stored_file.metadata.id),
        },
    )
