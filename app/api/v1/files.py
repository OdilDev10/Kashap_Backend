"""File download endpoints - R2/Local storage."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse

from app.dependencies import get_current_user
from app.models.user import User
from app.services.storage_service import storage_service
from app.core.exceptions import NotFoundException

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/{file_path:path}", response_model=None)
async def download_file(
    file_path: str,
    current_user: User = Depends(get_current_user),
) -> FileResponse | StreamingResponse:
    """
    Download file from storage (R2 or local).

    Args:
        file_path: Path to file (e.g., "vouchers/2026-03/abcd1234.jpg")

    Returns:
        File content with appropriate headers
    """
    try:
        # Validate path doesn't contain .. (security)
        if ".." in file_path:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid file path",
            )

        # Download file
        file_content = await storage_service.download(file_path)

        # Determine media type based on extension
        media_type = "application/octet-stream"
        if file_path.endswith((".jpg", ".jpeg")):
            media_type = "image/jpeg"
        elif file_path.endswith(".png"):
            media_type = "image/png"
        elif file_path.endswith(".pdf"):
            media_type = "application/pdf"
        elif file_path.endswith(".gif"):
            media_type = "image/gif"

        # Return file
        return StreamingResponse(
            iter([file_content]),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={file_path.split('/')[-1]}"},
        )

    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/presigned/{file_path:path}")
async def get_presigned_url(
    file_path: str,
    expires_in: int = 3600,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get presigned URL for file download (R2 only).

    Args:
        file_path: Path to file
        expires_in: URL expiration time in seconds (default 1 hour)

    Returns:
        Presigned URL dict
    """
    try:
        # Validate path
        if ".." in file_path:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid file path",
            )

        # Generate presigned URL
        url = await storage_service.generate_url(file_path, expires_in=expires_in)

        return {
            "file_path": file_path,
            "presigned_url": url,
            "expires_in": expires_in,
        }

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/{file_path:path}")
async def delete_file(
    file_path: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Delete file from storage.

    Note: Only files in 'temp' or 'processing' folders can be deleted by users.
    Production files require admin access.
    """
    try:
        # Security: only allow deletion of temporary files
        if not (file_path.startswith("temp/") or file_path.startswith("processing/")):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only delete temporary files",
            )

        if ".." in file_path:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid file path",
            )

        # Delete file
        await storage_service.delete(file_path)

        return {"message": f"File {file_path} deleted successfully"}

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
