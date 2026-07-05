from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class GenerateRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""
    model: str = ""
    steps: int = 4
    guidance: float = 3.5
    seed: Optional[int] = None
    width: int = 1024
    height: int = 1024
    batch_count: int = 1


class Img2ImgRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""
    model: str = ""
    steps: int = 4
    guidance: float = 3.5
    seed: Optional[int] = None
    strength: float = 0.8
    image_path: str = ""
    width: int = 1024
    height: int = 1024


class ImageRecordResponse(BaseModel):
    id: int
    prompt: str
    negative_prompt: str
    seed: int
    model: str
    width: int
    height: int
    steps: int
    guidance: float
    image_path: str
    thumbnail_path: str
    generation_time: float
    favorite: bool
    batch_total: int
    batch_index: int
    create_time: datetime

    class Config:
        from_attributes = True


class PromptTemplateCreate(BaseModel):
    title: str
    content: str
    category: str = "custom"
    favorite: bool = False


class PromptTemplateUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    favorite: Optional[bool] = None


class PromptTemplateResponse(BaseModel):
    id: int
    title: str
    content: str
    category: str
    favorite: bool
    create_time: datetime

    class Config:
        from_attributes = True


class TaskResponse(BaseModel):
    id: int
    task_id: str
    type: str
    status: str
    progress: int
    total_steps: int
    current_step: int
    elapsed: float
    prompt: str
    result_path: str
    error: str
    create_time: datetime

    class Config:
        from_attributes = True


class ModelResponse(BaseModel):
    id: int
    name: str
    path: str
    model_type: str
    quantization: str
    size_bytes: int
    is_default: bool
    create_time: datetime

    class Config:
        from_attributes = True


class SettingUpdate(BaseModel):
    key: str
    value: str


class ImageUpdate(BaseModel):
    favorite: Optional[bool] = None


class PromptEnhanceRequest(BaseModel):
    prompt: str
    style: str = "enhance"
    language: str = "en"
