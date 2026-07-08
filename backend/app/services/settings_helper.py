import os
import shutil
from typing import Dict, Optional, List

from sqlalchemy.orm import Session

from ..models import Setting

# Defaults
DEFAULT_MODEL = "mlx-community/flux2-klein-4b-4bit"
HF_CACHE_DIR_DEFAULT = os.path.expanduser("~/.cache/huggingface/hub")
OUTPUT_DIR_DEFAULT = "./output"
UPLOAD_DIR_DEFAULT = "./uploads"
SCAN_DIRS_DEFAULT = [
    os.path.expanduser("~/Models"),
    os.path.expanduser("~/Downloads/models"),
]


def get_settings(db: Session) -> Dict[str, str]:
    """Return all settings as a flat dict (key → value)."""
    records = db.query(Setting).all()
    return {r.key: r.value for r in records}


def get_setting(settings_dict: Dict[str, str], key: str, default: str = "") -> str:
    """Get a single setting with fallback."""
    return settings_dict.get(key, default)


def resolve_mlux_cli(settings_dict: Dict[str, str]) -> Optional[str]:
    """Return custom mlux executable path from settings, or auto-detect via shutil.which."""
    custom = settings_dict.get("mlux_executable_path", "").strip()
    if custom:
        if os.path.isfile(custom) and os.access(custom, os.X_OK):
            return custom
    return _pick_cli()


def _pick_cli() -> Optional[str]:
    cli = shutil.which("mflux-generate-flux2")
    if cli:
        return cli
    return shutil.which("mflux-generate")


def resolve_cache_dir(settings_dict: Dict[str, str]) -> str:
    """Return custom model cache directory or default."""
    custom = settings_dict.get("model_cache_dir", "").strip()
    if custom:
        return os.path.expanduser(custom)
    return HF_CACHE_DIR_DEFAULT


def resolve_output_dir(settings_dict: Dict[str, str]) -> str:
    """Return custom output directory. Priority: settings > env > default."""
    custom = settings_dict.get("output_dir", "").strip()
    if custom:
        return os.path.expanduser(custom)
    return os.getenv("OUTPUT_DIR", OUTPUT_DIR_DEFAULT)


def resolve_upload_dir(settings_dict: Dict[str, str]) -> str:
    """Return custom upload directory. Priority: settings > env > default."""
    custom = settings_dict.get("upload_dir", "").strip()
    if custom:
        return os.path.expanduser(custom)
    return os.getenv("UPLOAD_DIR", UPLOAD_DIR_DEFAULT)


def resolve_scan_dirs(settings_dict: Dict[str, str]) -> List[str]:
    """Return custom scan directories (comma-separated) or defaults."""
    custom = settings_dict.get("model_scan_dirs", "").strip()
    if custom:
        return [os.path.expanduser(d.strip()) for d in custom.split(",") if d.strip()]
    return list(SCAN_DIRS_DEFAULT)


def resolve_default_model(settings_dict: Dict[str, str]) -> str:
    """Return custom default model or hardcoded default."""
    custom = settings_dict.get("default_model", "").strip()
    if custom:
        return custom
    return DEFAULT_MODEL
