import json
import random
import threading
import time
import uuid
import asyncio
from typing import Dict, Optional, Callable
from collections import deque

from sqlalchemy.orm import Session

from ..logger import get_logger
from ..database import SessionLocal
from ..models import TaskRecord
from ..services.generator import generate_image

log = get_logger("task_queue")


class TaskQueue:
    def __init__(self):
        self._queue = deque()
        self._tasks: Dict[str, dict] = {}
        self._current_task: Optional[str] = None
        self._lock = threading.Lock()
        self._worker = threading.Thread(target=self._process_loop, daemon=True)
        self._running = True
        self._progress_callback: Optional[Callable] = None
        self._broadcast_callback: Optional[Callable] = None
        self._worker.start()
        log.info("Task queue worker started")

    def set_progress_callback(self, callback):
        self._progress_callback = callback

    def set_broadcast_callback(self, callback):
        self._broadcast_callback = callback

    def add_task(self, task_data: dict) -> str:
        task_id = str(uuid.uuid4())
        task_data["task_id"] = task_id

        with self._lock:
            self._tasks[task_id] = {
                "id": task_id,
                "data": task_data,
                "status": "waiting",
                "progress": 0,
                "total_steps": 0,
                "current_step": 0,
                "elapsed": 0.0,
                "queued_at": time.time(),
                "started_at": None,
            }
            self._queue.append(task_id)

        qsize = len(self._queue)
        ttype = task_data.get("type", "text2img")
        log.info("task %s queued [type=%s] [queue=%s]", task_id[:8], ttype, qsize)
        _save_task_to_db(task_id, task_data, "waiting")
        return task_id

    def cancel_task(self, task_id: str) -> bool:
        with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                if task["status"] in ("waiting", "running"):
                    task["status"] = "cancelled"
                    _update_task_status(task_id, "cancelled")
                    log.info("task %s cancelled", task_id[:8])
                    return True
    def cancel_all(self):
        with self._lock:
            for task_id, task in list(self._tasks.items()):
                if task["status"] in ("waiting", "running"):
                    _update_task_status(task_id, "cancelled")
                del self._tasks[task_id]
            self._current_task = None
            log.info("clear-all: removed all tasks from queue")

    def get_task(self, task_id: str) -> Optional[dict]:
        with self._lock:
            return self._tasks.get(task_id)

    def get_all_tasks(self) -> list:
        with self._lock:
            tasks = [
                {
                    "task_id": t["id"],
                    "type": t["data"].get("type", "text2img"),
                    "status": t["status"],
                    "progress": t["progress"],
                    "total_steps": t["total_steps"],
                    "current_step": t["current_step"],
                    "elapsed": t["elapsed"],
                    "prompt": t["data"].get("prompt", ""),
                    "queued_at": t.get("queued_at"),
                    "started_at": t.get("started_at"),
                }
                for t in self._tasks.values()
            ]
            tasks.sort(key=lambda t: t.get("queued_at", 0), reverse=True)
            return tasks
    def retry_task(self, task_id: str) -> Optional[str]:
        with self._lock:
            if task_id in self._tasks:
                old = self._tasks[task_id]
                if old["status"] in ("completed", "failed", "cancelled"):
                    new_id = str(uuid.uuid4())
                    new_data = dict(old["data"])
                    new_data["task_id"] = new_id
                    self._tasks[new_id] = {
                        "id": new_id,
                        "data": new_data,
                        "status": "waiting",
                        "progress": 0,
                        "total_steps": 0,
                        "current_step": 0,
                        "elapsed": 0.0,
                        "queued_at": time.time(),
                        "started_at": None,
                    }
                    self._queue.append(new_id)
                    _save_task_to_db(new_id, new_data, "waiting")
                    log.info("task %s retried as %s", task_id[:8], new_id[:8])
                    return new_id
        return None

    def _process_loop(self):
        while self._running:
            task_id = None
            with self._lock:
                if self._queue and self._current_task is None:
                    task_id = self._queue.popleft()
                    self._current_task = task_id

            if task_id is None:
                time.sleep(0.5)
                continue

            with self._lock:
                if task_id in self._tasks:
                    self._tasks[task_id]["status"] = "running"
                    self._tasks[task_id]["started_at"] = time.time()
                _update_task_status(task_id, "running")

            log.info("task %s starting...", task_id[:8])
            task_data = None
            with self._lock:
                if task_id in self._tasks:
                    task_data = self._tasks[task_id]["data"]

            if task_data:
                try:
                    start = time.time()
                    self._run_generation(task_id, task_data)
                    elapsed = time.time() - start
                    log.info("task %s completed in %.1fs", task_id[:8], elapsed)
                except Exception as e:
                    error_msg = str(e)
                    elapsed = time.time() - start
                    log.error("task %s failed after %.1fs: %s", task_id[:8], elapsed, error_msg[:200])
                    with self._lock:
                        if task_id in self._tasks:
                            self._tasks[task_id]["status"] = "failed"
                            self._tasks[task_id]["error"] = error_msg
                        _update_task_status(task_id, "failed", error=error_msg)
                    if self._broadcast_callback:
                        self._broadcast_callback({
                            "type": "task_error",
                            "task_id": task_id,
                            "error": error_msg,
                        })

            with self._lock:
                self._current_task = None

    def _run_generation(self, task_id: str, task_data: dict):
        ttype = task_data.get("type", "text2img")
        params = task_data.get("params", {})
        total_steps = params.get("steps", 4)

        def on_progress(tid, msg, current_step, _total, elapsed):
            pct = int((current_step / max(total_steps, 1)) * 100)
            with self._lock:
                if tid in self._tasks:
                    self._tasks[tid]["progress"] = min(pct, 100)
                    self._tasks[tid]["total_steps"] = total_steps
                    self._tasks[tid]["current_step"] = current_step
                    self._tasks[tid]["elapsed"] = elapsed
                    if self._progress_callback:
                        self._progress_callback(tid, msg, current_step, total_steps, elapsed)

        try:
            if ttype == "text2img":
                base_seed = params.get("seed") or random.randint(0, 2147483647)
                for i in range(params.get("batch_count", 1)):
                    log.debug("task %s generating batch %s/%s", task_id[:8], i + 1, params.get("batch_count", 1))
                    result = generate_image(
                        prompt=params.get("prompt", ""),
                        task_id=task_id,
                        negative_prompt=params.get("negative_prompt", ""),
                        model=params.get("model", ""),
                        steps=params.get("steps", 4),
                        guidance=params.get("guidance", 3.5),
                        seed=base_seed + i,
                        width=params.get("width", 1024),
                        height=params.get("height", 1024),
                        batch_count=params.get("batch_count", 1),
                        batch_index=i,
                        on_progress=on_progress,
                    )
            elif ttype == "img2img":
                result = generate_image(
                    prompt=params.get("prompt", ""),
                    task_id=task_id,
                    negative_prompt=params.get("negative_prompt", ""),
                    model=params.get("model", ""),
                    steps=params.get("steps", 4),
                    guidance=params.get("guidance", 3.5),
                    seed=params.get("seed"),
                    width=params.get("width", 1024),
                    height=params.get("height", 1024),
                    batch_count=1,
                    batch_index=0,
                    strength=params.get("strength", 0.8),
                    image_path=params.get("image_path", ""),
                    on_progress=on_progress,
                )
            else:
                log.warning("task %s unknown type: %s", task_id[:8], ttype)
                result = None

            with self._lock:
                if task_id in self._tasks:
                    self._tasks[task_id]["status"] = "completed"
                    self._tasks[task_id]["progress"] = 100
                    if result:
                        self._tasks[task_id]["result_path"] = result
                    _update_task_status(task_id, "completed", result_path=result)

            if result and self._broadcast_callback:
                self._broadcast_callback({
                    "type": "task_completed",
                    "task_id": task_id,
                    "result_path": result,
                })
        except Exception as e:
            raise

    def stop(self):
        log.info("Stopping task queue worker...")
        self._running = False


def _save_task_to_db(task_id: str, task_data: dict, status: str):
    try:
        db = SessionLocal()
        record = TaskRecord(
            task_id=task_id,
            type=task_data.get("type", "text2img"),
            status=status,
            prompt=task_data.get("params", {}).get("prompt", ""),
            params=json.dumps(task_data),
        )
        db.add(record)
        db.commit()
        db.close()
    except Exception as e:
        log.error("Failed to save task %s to DB: %s", task_id[:8], e)


def _update_task_status(task_id: str, status: str, error: str = "", result_path: str = ""):
    try:
        db = SessionLocal()
        record = db.query(TaskRecord).filter(TaskRecord.task_id == task_id).first()
        if record:
            record.status = status
            if error:
                record.error = error
            if result_path:
                record.result_path = result_path
            db.commit()
        db.close()
    except Exception as e:
        log.error("Failed to update task %s status: %s", task_id[:8], e)


task_queue = TaskQueue()
