import os
import re
import glob
from typing import List, Dict

from ..logger import get_logger

log = get_logger("model_scanner")

HF_CACHE_DIR = os.path.expanduser("~/.cache/huggingface/hub")
SCAN_DIRS = [
    os.path.expanduser("~/Models"),
    os.path.expanduser("~/Downloads/models"),
]

MODEL_PATTERNS = [
    "**/*.safetensors",
    "**/*.ckpt",
    "**/*.pt",
    "**/*.pth",
    "**/*.bin",
    "**/*.gguf",
]

HF_MODEL_PREFIX = "models--"


def _scan_hf_cache() -> List[Dict]:
    found = []
    if not os.path.isdir(HF_CACHE_DIR):
        return found

    for entry in os.listdir(HF_CACHE_DIR):
        if not entry.startswith(HF_MODEL_PREFIX):
            continue

        repo_dir = os.path.join(HF_CACHE_DIR, entry)
        if not os.path.isdir(repo_dir):
            continue

        repo_id = entry[len(HF_MODEL_PREFIX):].replace("--", "/")
        snapshots_dir = os.path.join(repo_dir, "snapshots")
        if not os.path.isdir(snapshots_dir):
            continue

        for snap_id in os.listdir(snapshots_dir):
            snap_path = os.path.join(snapshots_dir, snap_id)
            if not os.path.isdir(snap_path):
                continue

            total_size = 0
            file_count = 0
            safetensors_count = 0
            quantization = "unknown"

            for root, dirs, files in os.walk(snap_path):
                for f in files:
                    fpath = os.path.join(root, f)
                    try:
                        size = os.path.getsize(fpath)
                    except OSError:
                        continue
                    total_size += size
                    file_count += 1
                    if f.endswith(".safetensors"):
                        safetensors_count += 1

            q_lower = repo_id.lower()
            if any(kw in q_lower for kw in ("4bit", "q4", "int4")):
                quantization = "INT4"
            elif any(kw in q_lower for kw in ("8bit", "q8", "int8")):
                quantization = "INT8"
            elif "fp16" in q_lower:
                quantization = "FP16"
            elif "fp32" in q_lower:
                quantization = "FP32"

            name = repo_id.split("/")[-1] if "/" in repo_id else repo_id

            if safetensors_count == 0:
                log.debug("  skip %s (no safetensors)", repo_id)
                continue

            found.append({
                "name": name,
                "repo_id": repo_id,
                "path": snap_path,
                "model_type": "mflux",
                "quantization": quantization,
                "size_bytes": total_size,
                "file_count": file_count,
                "last_modified": os.path.getmtime(snap_path),
            })
            log.debug("  HF model: %s (%s, %s files, %s)",
                      repo_id, quantization, safetensors_count,
                      _format_size(total_size))

    return found


def _scan_other_dirs() -> List[Dict]:
    found = []
    seen_paths = set()

    for scan_dir in SCAN_DIRS:
        if not os.path.isdir(scan_dir):
            log.debug("scan dir not found: %s", scan_dir)
            continue

        log.debug("scanning: %s", scan_dir)
        for pattern in MODEL_PATTERNS:
            for filepath in glob.glob(os.path.join(scan_dir, pattern), recursive=True):
                if filepath in seen_paths:
                    continue
                seen_paths.add(filepath)

                stat = os.stat(filepath)
                name = os.path.splitext(os.path.basename(filepath))[0]
                quant = _detect_quantization(name)

                log.debug("  file: %s (%s, %s)", name, quant, _format_size(stat.st_size))
                found.append({
                    "name": name,
                    "repo_id": name,
                    "path": filepath,
                    "model_type": "mflux",
                    "quantization": quant,
                    "size_bytes": stat.st_size,
                    "file_count": 1,
                    "last_modified": stat.st_mtime,
                })

    return found


def _detect_quantization(name: str) -> str:
    lower = name.lower()
    keywords = {
        "4bit": "INT4", "q4": "INT4", "int4": "INT4",
        "8bit": "INT8", "q8": "INT8", "int8": "INT8",
        "fp16": "FP16", "fp32": "FP32",
        "bf16": "BF16",
        "gguf": "GGUF",
    }
    for kw, label in keywords.items():
        if kw in lower:
            return label
    return "unknown"


def _format_size(bytes_val: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if bytes_val < 1024:
            return f"{bytes_val:.1f}{unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f}PB"


def scan_models() -> List[Dict]:
    log.info("Starting model scan...")
    found = _scan_hf_cache() + _scan_other_dirs()
    log.info("Model scan complete: %s models found", len(found))
    for m in found:
        log.info("  %s | %s | %s | %s",
                 m["name"], m["repo_id"],
                 m["quantization"], _format_size(m["size_bytes"]))
    return found
