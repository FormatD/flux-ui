from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..logger import get_logger
from ..database import get_db
from ..models import Setting
from ..schemas.schemas import SettingUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])
log = get_logger("api.settings")


@router.get("")
async def get_settings(db: Session = Depends(get_db)):
    records = db.query(Setting).all()
    return {r.key: r.value for r in records}


@router.post("")
async def update_setting(req: SettingUpdate, db: Session = Depends(get_db)):
    record = db.query(Setting).filter(Setting.key == req.key).first()
    if record:
        record.value = req.value
    else:
        record = Setting(key=req.key, value=req.value)
        db.add(record)
    db.commit()
    log.info("setting %s = %s", req.key, req.value[:50] if len(req.value) > 50 else req.value)
    return {"status": "ok", "key": req.key, "value": req.value}
