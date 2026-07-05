import os
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional

from ..logger import get_logger
from ..database import get_db
from ..models import ImageRecord
from ..schemas.schemas import ImageRecordResponse, ImageUpdate

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./output")


def _resolve_path(url_path: str) -> str:
    """Convert a URL path (e.g. /api/output/xxx.png) to a local filesystem path."""
    return os.path.join(OUTPUT_DIR, os.path.basename(url_path))


router = APIRouter(prefix="/api/images", tags=["images"])
log = get_logger("api.images")


@router.get("", response_model=list[ImageRecordResponse])
async def list_images(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    favorite: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    query = db.query(ImageRecord)

    if search:
        query = query.filter(ImageRecord.prompt.ilike(f"%{search}%"))
    if favorite is not None:
        query = query.filter(ImageRecord.favorite == favorite)

    total = query.count()
    records = query.order_by(desc(ImageRecord.create_time)).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    log.debug("list_images page=%s size=%s total=%s", page, page_size, total)
    return records


@router.get("/{image_id}", response_model=ImageRecordResponse)
async def get_image(image_id: int, db: Session = Depends(get_db)):
    record = db.query(ImageRecord).filter(ImageRecord.id == image_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Image not found")
    return record


@router.patch("/{image_id}")
async def update_image(image_id: int, update: ImageUpdate, db: Session = Depends(get_db)):
    record = db.query(ImageRecord).filter(ImageRecord.id == image_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Image not found")

    if update.favorite is not None:
        record.favorite = update.favorite
        log.info("image %s favorite=%s", image_id, update.favorite)

    db.commit()
    return {"status": "ok"}


@router.delete("/{image_id}")
async def delete_image(image_id: int, db: Session = Depends(get_db)):
    record = db.query(ImageRecord).filter(ImageRecord.id == image_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Image not found")

    if record.image_path:
        path = _resolve_path(record.image_path)
        if os.path.exists(path):
            os.remove(path)
    if record.thumbnail_path:
        path = _resolve_path(record.thumbnail_path)
        if os.path.exists(path):
            os.remove(path)

    db.delete(record)
    db.commit()
    log.info("image %s deleted", image_id)
    return {"status": "ok"}


@router.delete("")
async def batch_delete(ids: list[int] = Body(...), db: Session = Depends(get_db)):
    records = db.query(ImageRecord).filter(ImageRecord.id.in_(ids)).all()
    for record in records:
        if record.image_path:
            path = _resolve_path(record.image_path)
            if os.path.exists(path):
                os.remove(path)
        if record.thumbnail_path:
            path = _resolve_path(record.thumbnail_path)
            if os.path.exists(path):
                os.remove(path)
        db.delete(record)
    db.commit()
    log.info("batch deleted %s images", len(records))
    return {"status": "ok", "deleted": len(records)}
