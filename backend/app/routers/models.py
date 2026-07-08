import uuid
import threading
import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..logger import get_logger
from ..database import get_db
from ..models import ModelRecord
from ..schemas.schemas import ModelResponse
from ..services.model_scanner import scan_models
from ..services.settings_helper import get_settings, resolve_cache_dir, resolve_scan_dirs
from ..websocket_manager import manager, scan_progress_callback

router = APIRouter(prefix="/api/models", tags=["models"])
log = get_logger("api.models")


@router.get("", response_model=list[ModelResponse])
async def list_models(db: Session = Depends(get_db)):
    records = db.query(ModelRecord).order_by(desc(ModelRecord.create_time)).all()
    log.debug("list_models count=%s", len(records))
    return records


@router.post("/scan")
async def scan_local_models(db: Session = Depends(get_db)):
    task_id = str(uuid.uuid4())
    log.info("Starting async model scan (task=%s)...", task_id)

    # Load settings from DB for the scanner
    settings_dict = get_settings(db)
    cache_dir = resolve_cache_dir(settings_dict)
    dirs = resolve_scan_dirs(settings_dict)

    def _run_scan(task_id: str, model_cache_dir: str, scan_dirs_list):
        from ..database import SessionLocal
        from ..models import ModelRecord as MR
        log.info("Background scan thread started (task=%s)", task_id)

        def _progress(model_name, message, current, total, elapsed):
            scan_progress_callback(task_id, model_name, message, current, total, elapsed)

        scan_start = time.time()
        try:
            found = scan_models(
                progress_callback=_progress,
                timeout=300,
                model_cache_dir=model_cache_dir,
                scan_dirs=scan_dirs_list,
            )
            elapsed = time.time() - scan_start
            log.info("Background scan found %d models (task=%s)", len(found), task_id)

            bdb = SessionLocal()
            try:
                bdb.query(MR).delete()
                added = 0
                for item in found:
                    record = MR(
                        name=item["name"],
                        path=item.get("repo_id", item["path"]),
                        model_type=item["model_type"],
                        quantization=item["quantization"],
                        size_bytes=item["size_bytes"],
                    )
                    bdb.add(record)
                    added += 1
                bdb.commit()
                log.info("Background scan saved %d models (task=%s)", added, task_id)
            finally:
                bdb.close()

            scan_progress_callback(task_id, "_done", f"Scan complete: {len(found)} models",
                                   100, 100, elapsed)
        except Exception as e:
            log.error("Background scan failed (task=%s): %s", task_id, e)
            scan_progress_callback(task_id, "_error", f"Scan failed: {e}",
                                   100, 100, time.time() - scan_start)

    thread = threading.Thread(
        target=_run_scan, args=(task_id, cache_dir, dirs), daemon=True
    )
    thread.start()

    return {"task_id": task_id, "status": "scanning"}


@router.get("/scan-result/{task_id}")
async def get_scan_result(task_id: str, db: Session = Depends(get_db)):
    """Legacy sync scan kept for backward-compatible querying."""
    records = db.query(ModelRecord).order_by(desc(ModelRecord.create_time)).all()
    return {
        "task_id": task_id,
        "scanned": len(records),
        "models": records,
    }


@router.post("/scan-sync", include_in_schema=False)
async def scan_local_models_sync(db: Session = Depends(get_db)):
    """Original synchronous scan endpoint, kept for backward compatibility."""
    log.info("Running sync model scan...")

    # Load settings from DB
    settings_dict = get_settings(db)
    cache_dir = resolve_cache_dir(settings_dict)
    dirs = resolve_scan_dirs(settings_dict)

    db.query(ModelRecord).delete()
    db.commit()
    log.info("Cleared old model records")

    found = scan_models(model_cache_dir=cache_dir, scan_dirs=dirs)
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
