from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..logger import get_logger
from ..database import get_db
from ..models import PromptTemplate
from ..schemas.schemas import (
    PromptTemplateCreate,
    PromptTemplateUpdate,
    PromptTemplateResponse,
    PromptEnhanceRequest,
)

router = APIRouter(prefix="/api/prompts", tags=["prompts"])
log = get_logger("api.prompts")


@router.get("", response_model=list[PromptTemplateResponse])
async def list_prompts(
    category: str = "",
    favorite: bool = None,
    db: Session = Depends(get_db),
):
    query = db.query(PromptTemplate)
    if category:
        query = query.filter(PromptTemplate.category == category)
    if favorite is not None:
        query = query.filter(PromptTemplate.favorite == favorite)
    records = query.order_by(desc(PromptTemplate.create_time)).all()
    log.debug("list_prompts category=%s count=%s", category or "*", len(records))
    return records


@router.post("", response_model=PromptTemplateResponse)
async def create_prompt(req: PromptTemplateCreate, db: Session = Depends(get_db)):
    if not req.title.strip():
        raise HTTPException(status_code=400, detail="Title is required")
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="Content is required")

    record = PromptTemplate(
        title=req.title,
        content=req.content,
        category=req.category,
        favorite=req.favorite,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    log.info("prompt created id=%s title=%s category=%s", record.id, record.title, record.category)
    return record


@router.put("/{prompt_id}", response_model=PromptTemplateResponse)
async def update_prompt(
    prompt_id: int,
    req: PromptTemplateUpdate,
    db: Session = Depends(get_db),
):
    record = db.query(PromptTemplate).filter(PromptTemplate.id == prompt_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Prompt not found")

    if req.title is not None:
        record.title = req.title
    if req.content is not None:
        record.content = req.content
    if req.category is not None:
        record.category = req.category
    if req.favorite is not None:
        record.favorite = req.favorite

    db.commit()
    db.refresh(record)
    log.info("prompt %s updated", prompt_id)
    return record


@router.delete("/{prompt_id}")
async def delete_prompt(prompt_id: int, db: Session = Depends(get_db)):
    record = db.query(PromptTemplate).filter(PromptTemplate.id == prompt_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Prompt not found")
    db.delete(record)
    db.commit()
    log.info("prompt %s deleted", prompt_id)
    return {"status": "ok"}


@router.post("/enhance")
async def enhance_prompt(req: PromptEnhanceRequest):
    enhanced = _enhance_with_template(req.prompt, req.style, req.language)
    log.info("prompt enhanced style=%s lang=%s | %.50s -> %.50s", req.style, req.language, req.prompt, enhanced)
    return {"original": req.prompt, "enhanced": enhanced}


def _enhance_with_template(prompt: str, style: str, language: str) -> str:
    style_prefixes = {
        "enhance": "masterpiece, best quality, highly detailed, ",
        "realistic": "photorealistic, ultra detailed, 8K, realistic lighting, ",
        "anime": "anime style, cel shaded, vibrant colors, ",
        "cinematic": "cinematic lighting, dramatic composition, film grain, ",
    }

    quality_suffix = ", high quality, detailed, sharp focus"

    prefix = style_prefixes.get(style, style_prefixes["enhance"])
    enhanced = prefix + prompt + quality_suffix

    if language == "zh" and not _is_english(prompt):
        enhanced = f"masterpiece, best quality, {prompt}, highly detailed, sharp focus"

    return enhanced


def _is_english(text: str) -> bool:
    try:
        text.encode("ascii")
        return True
    except UnicodeEncodeError:
        return False
