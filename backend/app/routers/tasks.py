from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..logger import get_logger
from ..database import get_db
from ..models import TaskRecord
from ..schemas.schemas import TaskResponse
from ..services.task_queue import task_queue

router = APIRouter(prefix="/api/tasks", tags=["tasks"])
log = get_logger("api.tasks")


@router.get("", response_model=list[TaskResponse])
async def list_tasks(db: Session = Depends(get_db)):
    return db.query(TaskRecord).order_by(desc(TaskRecord.create_time)).limit(50).all()


@router.get("/queue")
async def get_queue():
    tasks = task_queue.get_all_tasks()
    return tasks


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str):
    log.info("Cancelling task %s", task_id[:8])
    ok = task_queue.cancel_task(task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Task not found or not cancellable")
    return {"status": "cancelled"}


@router.post("/cancel-all")
async def cancel_all_tasks():
    log.info("Cancelling all tasks")
    task_queue.cancel_all()
    return {"status": "ok"}


@router.post("/{task_id}/retry")
async def retry_task(task_id: str):
    log.info("Retrying task %s", task_id[:8])
    new_id = task_queue.retry_task(task_id)
    if not new_id:
        raise HTTPException(status_code=404, detail="Task not found or not retryable")
    return {"task_id": new_id, "status": "queued"}


@router.get("/{task_id}")
async def get_task(task_id: str):
    task = task_queue.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
