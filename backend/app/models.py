from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean, BigInteger
from sqlalchemy.sql import func
from .database import Base


class ImageRecord(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    prompt = Column(Text, nullable=False)
    negative_prompt = Column(Text, default="")
    seed = Column(BigInteger, nullable=False)
    model = Column(String(255), nullable=False)
    width = Column(Integer, default=1024)
    height = Column(Integer, default=1024)
    steps = Column(Integer, default=4)
    guidance = Column(Float, default=3.5)
    strength = Column(Float, default=0.8, nullable=True)
    image_path = Column(String(512), nullable=False)
    thumbnail_path = Column(String(512), default="")
    generation_time = Column(Float, default=0.0)
    favorite = Column(Boolean, default=False)
    batch_total = Column(Integer, default=1)
    batch_index = Column(Integer, default=0)
    task_id = Column(String(64), default="")
    create_time = Column(DateTime(timezone=True), server_default=func.now())


class PromptTemplate(Base):
    __tablename__ = "prompts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(64), default="custom")
    favorite = Column(Boolean, default=False)
    create_time = Column(DateTime(timezone=True), server_default=func.now())


class TaskRecord(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    task_id = Column(String(64), unique=True, nullable=False)
    type = Column(String(32), default="text2img")
    status = Column(String(16), default="waiting")
    progress = Column(Integer, default=0)
    total_steps = Column(Integer, default=0)
    current_step = Column(Integer, default=0)
    elapsed = Column(Float, default=0.0)
    prompt = Column(Text, default="")
    params = Column(Text, default="")
    result_path = Column(String(512), default="")
    error = Column(Text, default="")
    create_time = Column(DateTime(timezone=True), server_default=func.now())


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String(128), primary_key=True)
    value = Column(Text, default="")


class ModelRecord(Base):
    __tablename__ = "models"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    path = Column(String(512), nullable=False)
    model_type = Column(String(64), default="mflux")
    quantization = Column(String(32), default="")
    size_bytes = Column(BigInteger, default=0)
    is_default = Column(Boolean, default=False)
    last_used = Column(DateTime(timezone=True), nullable=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
