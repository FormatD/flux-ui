from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..logger import get_logger
from ..database import get_db
from ..models import ModelRecord
from ..schemas.schemas import ModelResponse
from ..services.model_scanner import scan_models

router = APIRouter(prefix="/api/models", tags=["models"])
log = get_logger("api.models")


@router.get("", response_model=list[ModelResponse])
async def list_models(db: Session = Depends(get_db)):
    records = db.query(ModelRecord).order_by(desc(ModelRecord.create_time)).all()
    log.debug("list_models count=%s", len(records))
    return records


@router.post("/scan")
async def scan_local_models(db: Session = Depends(get_db)):
    log.info("Starting model scan...")

    db.query(ModelRecord).delete()
    db.commit()
    log.info("Cleared old model records")

    found = scan_models()
    added = 0

    for item in found:
        record = ModelRecord(
            name=item["name"],
            path=item.get("repo_id", item["path"]),
            model_type=item["model_type"],
            quantization=item["quantization"],
            size_bytes=item["size_bytes"],
        )
        db.add(record)
        added += 1

    db.commit()
    log.info("Model scan complete: %s found, %s saved", len(found), added)
    return {"scanned": len(found), "added": added}


@router.delete("/{model_id}")
async def delete_model(model_id: int, db: Session = Depends(get_db)):
    record = db.query(ModelRecord).filter(ModelRecord.id == model_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Model not found")
    db.delete(record)
    db.commit()
    log.info("model %s (%s) deleted", model_id, record.name)
    return {"status": "ok"}


@router.post("/{model_id}/default")
async def set_default_model(model_id: int, db: Session = Depends(get_db)):
    record = db.query(ModelRecord).filter(ModelRecord.id == model_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Model not found")

    db.query(ModelRecord).update({"is_default": False})
    record.is_default = True
    db.commit()
    log.info("default model set to %s", record.name)
    return {"status": "ok", "model": record.name}
