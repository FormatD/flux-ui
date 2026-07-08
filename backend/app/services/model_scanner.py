import os
import re
import glob
import threading
import time
from typing import List, Dict, Optional, Callable

from ..logger import get_logger

log = get_logger("model_scanner")

HF_CACHE_DIR = os.path.expanduser("~/.cache/huggingface/hub")
SCAN_DIRS = [
    os.path.expanduser("~/Models"),
    os.path.expanduser("~/Downloads/models"),
]
SCAN_DEFAULT_TIMEOUT = 300

MODEL_PATTERNS = [
    "**/*.safetensors",
    "**/*.ckpt",
    "**/*.pt",
    "**/*.pth",
    "**/*.bin",
    "**/*.gguf",
]

HF_MODEL_PREFIX = "models--"


def _check_timeout(start_time: float, timeout: float, cancel_event: Optional[threading.Event] = None) -> bool:
    if cancel_event and cancel_event.is_set():
        return True
    if timeout > 0 and time.time() - start_time >= timeout:
        return True
    return False


def _count_hf_models(hf_cache_dir: str = "") -> int:
    cache_dir = hf_cache_dir or HF_CACHE_DIR
    if not os.path.isdir(cache_dir):
        return 0
    count = 0
    for entry in os.listdir(cache_dir):
        if entry.startswith(HF_MODEL_PREFIX) and os.path.isdir(os.path.join(cache_dir, entry)):
            snap_dir = os.path.join(cache_dir, entry, "snapshots")
            if os.path.isdir(snap_dir) and os.listdir(snap_dir):
                count += 1
    return count


def _scan_hf_cache(hf_cache_dir: str = "",
                   progress_callback: Optional[Callable] = None,
                   start_time: float = 0,
                   timeout: float = 300,
                   cancel_event: Optional[threading.Event] = None) -> List[Dict]:
    cache_dir = hf_cache_dir or HF_CACHE_DIR
    found = []
    if not os.path.isdir(cache_dir):
        return found

    total_models = _count_hf_models(cache_dir)
    model_idx = 0

    for entry in os.listdir(cache_dir):
        if not entry.startswith(HF_MODEL_PREFIX):
            continue

        if _check_timeout(start_time, timeout, cancel_event):
            log.warning("HF cache scan timed out after %d models", model_idx)
            break

        repo_dir = os.path.join(cache_dir, entry)
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
                model_idx += 1
                if progress_callback:
                    progress_callback(repo_id, f"Skipping {name} (no .safetensors)",
                                      model_idx, total_models)
                continue

            model_idx += 1

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

            if progress_callback:
                progress_callback(repo_id, f"Found {name}", model_idx, total_models)

            log.debug("  HF model: %s (%s, %s files, %s)",
                      repo_id, quantization, safetensors_count,
                      _format_size(total_size))

    return found


def _scan_other_dirs(scan_dirs=None,
                     progress_callback: Optional[Callable] = None,
                     start_time: float = 0,
                     timeout: float = 300,
                     cancel_event: Optional[threading.Event] = None) -> List[Dict]:
    dirs = scan_dirs if scan_dirs is not None else SCAN_DIRS
    found = []
    seen_paths = set()

    for scan_dir in dirs:
        if not os.path.isdir(scan_dir):
            log.debug("scan dir not found: %s", scan_dir)
            continue

        if _check_timeout(start_time, timeout, cancel_event):
            log.warning("Other dirs scan timed out")
            break

        log.debug("scanning: %s", scan_dir)
        for pattern in MODEL_PATTERNS:
            if _check_timeout(start_time, timeout, cancel_event):
                break
            for filepath in glob.glob(os.path.join(scan_dir, pattern), recursive=True):
                if _check_timeout(start_time, timeout, cancel_event):
                    break
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


def scan_models(progress_callback: Optional[Callable] = None,
                timeout: float = 300,
                cancel_event: Optional[threading.Event] = None,
                model_cache_dir: str = "",
                scan_dirs: Optional[List[str]] = None) -> List[Dict]:
    log.info("Starting model scan (timeout=%ss)...", timeout)
    start_time = time.time()

    if progress_callback:
        progress_callback("_phase", "Scanning HuggingFace cache...", 0, 3, 0)

    found = _scan_hf_cache(model_cache_dir, progress_callback, start_time, timeout, cancel_event)

    if not _check_timeout(start_time, timeout, cancel_event):
        if progress_callback:
            progress_callback("_phase", "Scanning local directories...", 1, 3, 0)
        found += _scan_other_dirs(scan_dirs, progress_callback, start_time, timeout, cancel_event)

    elapsed = time.time() - start_time
    log.info("Model scan complete: %s models found in %.1fs", len(found), elapsed)

    for m in found:
        log.info("  %s | %s | %s | %s",
                 m["name"], m["repo_id"],
                 m["quantization"], _format_size(m["size_bytes"]))

    if _check_timeout(start_time, timeout, cancel_event):
        msg = f"Scan timed out after {elapsed:.0f}s, partial results: {len(found)} models"
        if progress_callback:
            progress_callback("_phase", msg, 3, 3, elapsed)
        log.warning("Model scan timed out after %.1fs, returning %s partial results", elapsed, len(found))
    elif progress_callback:
        progress_callback("_phase", f"Scan complete: {len(found)} models found", 3, 3, elapsed)

    return found
