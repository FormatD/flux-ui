import random
from fastapi import APIRouter, HTTPException, Depends

from ..logger import get_logger
from ..rate_limiter import rate_limiter
from ..schemas.schemas import GenerateRequest, Img2ImgRequest
from ..services.task_queue import task_queue

router = APIRouter(prefix="/api/generate", tags=["generate"])
log = get_logger("api.generate")


@router.post("/text2img")
async def text_to_image(req: GenerateRequest, _limiter=Depends(rate_limiter)):
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt is required")

    seed = req.seed if req.seed is not None else random.randint(0, 2147483647)

    log.info(
        "text2img queued | prompt=%.50s model=%s steps=%s seed=%s size=%sx%s batch=%s",
        req.prompt, req.model or "default", req.steps, seed, req.width, req.height, req.batch_count,
    )

    task_data = {
        "type": "text2img",
        "params": {
            "prompt": req.prompt,
            "negative_prompt": req.negative_prompt,
            "model": req.model,
            "steps": req.steps,
            "guidance": req.guidance,
            "seed": seed,
            "width": req.width,
            "height": req.height,
            "batch_count": req.batch_count,
        },
    }

    task_id = task_queue.add_task(task_data)
    return {"task_id": task_id, "seed": seed, "status": "queued"}


@router.post("/img2img")
async def image_to_image(req: Img2ImgRequest, _limiter=Depends(rate_limiter)):
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt is required")
    if not req.image_path:
        raise HTTPException(status_code=400, detail="Image path is required")

    seed = req.seed if req.seed is not None else random.randint(0, 2147483647)

    log.info(
        "img2img queued | prompt=%.50s model=%s strength=%s seed=%s size=%sx%s image=%s",
        req.prompt, req.model or "default", req.strength, seed, req.width, req.height, req.image_path,
    )

    task_data = {
        "type": "img2img",
        "params": {
            "prompt": req.prompt,
            "negative_prompt": req.negative_prompt,
            "model": req.model,
            "steps": req.steps,
            "guidance": req.guidance,
            "seed": seed,
            "strength": req.strength,
            "image_path": req.image_path,
            "width": req.width,
            "height": req.height,
        },
    }

    task_id = task_queue.add_task(task_data)
    return {"task_id": task_id, "seed": seed, "status": "queued"}
