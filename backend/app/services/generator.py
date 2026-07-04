import os
import time
import random
import signal
import subprocess
import shutil
from typing import Optional, Callable
from datetime import datetime

from ..logger import get_logger
from ..database import SessionLocal
from ..models import ImageRecord

log = get_logger("generator")

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

DEFAULT_MODEL = "mlx-community/flux2-klein-4b-4bit"
CACHE_DIR = os.path.expanduser("~/.cache/huggingface/hub")

MIN_DISK_MB = 100  # sufficient for output + temp files


def _check_disk_space(path: str):
    try:
        st = os.statvfs(path)
        free_mb = (st.f_bavail * st.f_frsize) / (1024 * 1024)
        if free_mb < MIN_DISK_MB:
            raise RuntimeError(
                f"Low disk space: {free_mb:.0f}MB free (need {MIN_DISK_MB}MB). "
                "Please free up disk space and try again."
            )
    except RuntimeError:
        raise
    except Exception:
        pass


def _find_cli(name: str) -> Optional[str]:
    return shutil.which(name)


def _resolve_model_path(model_name: str) -> str:
    if os.path.isfile(model_name) or os.path.isdir(model_name):
        return model_name
    candidates = [model_name]
    if "/" not in model_name:
        candidates.insert(0, f"mlx-community/{model_name}")
        candidates.insert(0, f"black-forest-labs/{model_name}")
    for name in candidates:
        safe_name = name.replace("/", "--")
        model_dir = os.path.join(CACHE_DIR, f"models--{safe_name}")
        if os.path.isdir(model_dir):
            snapshots = os.path.join(model_dir, "snapshots")
            if os.path.isdir(snapshots):
                for entry in os.listdir(snapshots):
                    snap_dir = os.path.join(snapshots, entry)
                    if os.path.isdir(snap_dir) and os.listdir(snap_dir):
                        log.debug("resolved model %s -> %s (cache: %s)", model_name, name, snap_dir)
                        return name
    return model_name


def _pick_cli(model: str) -> Optional[str]:
    model_lower = (model or "").lower()
    if any(kw in model_lower for kw in ("klein", "flux2", "flux.2")):
        cli = _find_cli("mflux-generate-flux2")
        if cli:
            return cli
    return _find_cli("mflux-generate-flux2") or _find_cli("mflux-generate")


def _url_path(filepath: str) -> str:
    rel = os.path.relpath(filepath, os.path.dirname(OUTPUT_DIR))
    return f"/api/output/{os.path.basename(filepath)}"


def generate_image(
    prompt: str,
    task_id: str,
    negative_prompt: str = "",
    model: str = "",
    steps: int = 4,
    guidance: float = 3.5,
    seed: Optional[int] = None,
    width: int = 1024,
    height: int = 1024,
    batch_count: int = 1,
    batch_index: int = 0,
    on_progress: Optional[Callable] = None,
    strength: Optional[float] = None,
    image_path: Optional[str] = None,
) -> Optional[str]:
    if seed is None:
        seed = random.randint(0, 2147483647)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{task_id}_{timestamp}.png"
    output_path = os.path.join(OUTPUT_DIR, filename)

    model_name = (model or DEFAULT_MODEL).strip()
    resolved = _resolve_model_path(model_name)
    steps = max(steps, 2)
    is_klein = "klein" in (resolved or model_name).lower()

    _check_disk_space(OUTPUT_DIR)

    log.info(
        "task=%s generate | prompt=%.50s model=%s resolved=%s steps=%s seed=%s size=%sx%s guidance=%s batch=%s/%s",
        task_id[:8], prompt, model_name, resolved, steps, seed, width, height,
        "1.0" if is_klein else guidance, batch_index + 1, batch_count,
    )

    if not os.path.exists(resolved) and not os.path.isdir(os.path.join(CACHE_DIR, f"models--{resolved.replace('/', '--')}")):
        log.warning("task=%s model '%s' not found locally, trying anyway", task_id[:8], resolved)

    cli = _pick_cli(model_name)
    if not cli:
        raise RuntimeError("No mflux CLI found. Install with: pip install mflux")

    log.debug("task=%s using CLI: %s", task_id[:8], cli)

    return _run_cli(
        cli=cli,
        prompt=prompt,
        task_id=task_id,
        output_path=output_path,
        negative_prompt=negative_prompt,
        model=resolved,
        steps=steps,
        guidance=guidance,
        seed=seed,
        width=width,
        height=height,
        batch_count=batch_count,
        batch_index=batch_index,
        on_progress=on_progress,
        strength=strength,
        image_path=image_path,
    )


def _run_cli(
    cli: str,
    prompt: str,
    task_id: str,
    output_path: str,
    negative_prompt: str = "",
    model: str = "",
    steps: int = 4,
    guidance: float = 3.5,
    seed: int = 0,
    width: int = 1024,
    height: int = 1024,
    batch_count: int = 1,
    batch_index: int = 0,
    on_progress: Optional[Callable] = None,
    strength: Optional[float] = None,
    image_path: Optional[str] = None,
) -> Optional[str]:
    cmd = [cli, "--model", model]
    cmd.extend(["--prompt", prompt])
    cmd.extend(["--steps", str(steps)])

    is_klein = "klein" in model.lower()
    if is_klein:
        cmd.extend(["--guidance", "1.0"])
    else:
        cmd.extend(["--guidance", str(guidance)])

    cmd.extend(["--seed", str(seed)])
    cmd.extend(["--width", str(width)])
    cmd.extend(["--height", str(height)])
    cmd.extend(["--output", output_path])

    if negative_prompt:
        is_klein_cmd = "klein" in model.lower() or "flux2" in model.lower()
        if is_klein_cmd:
            log.warning("task=%s negative_prompt not supported for FLUX.2, skipping", task_id[:8])
        else:
            cmd.extend(["--negative-prompt", negative_prompt])
    if strength is not None and image_path:
        cmd.extend(["--image-path", image_path])
        cmd.extend(["--image-strength", str(strength)])

    log.debug("task=%s shell command: %s", task_id[:8], " ".join(cmd))

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        start_time = time.time()
        step_count = 0

        for line in iter(process.stdout.readline, ""):
            line = line.strip()
            if not line:
                continue
            step_count += 1
            if on_progress:
                elapsed = time.time() - start_time
                on_progress(task_id, line, step_count, steps, elapsed)

        process.wait()

        if process.returncode != 0:
            error = process.stderr.read()
            log.error("task=%s CLI exit code=%s stderr=%.200s", task_id[:8], process.returncode, error)
            if process.returncode < 0:
                sig = -process.returncode
                raise RuntimeError(
                    f"CLI process terminated by signal {sig} (SIG{signal.Signals(sig).name}). "
                    "This may indicate insufficient memory or disk space."
                )
            raise RuntimeError(error.strip() or "CLI process failed")

        generation_time = time.time() - start_time
        log.info("task=%s CLI done in %.1fs, output=%s", task_id[:8], generation_time, output_path)

        if os.path.exists(output_path):
            size = os.path.getsize(output_path)
            image_url = _url_path(output_path)
            log.info("task=%s image saved: %s (%s bytes) url=%s", task_id[:8], output_path, size, image_url)
            _save_record(
                task_id=task_id,
                prompt=prompt,
                negative_prompt=negative_prompt,
                seed=seed,
                model=model,
                width=width,
                height=height,
                steps=steps,
                guidance=guidance,
                strength=strength,
                image_path=image_url,
                generation_time=generation_time,
                batch_total=batch_count,
                batch_index=batch_index,
            )
            return image_url
        else:
            log.error("task=%s output file not found: %s", task_id[:8], output_path)

    except Exception as e:
        log.error("task=%s CLI error: %s", task_id[:8], e)
        raise RuntimeError(f"Generation failed: {e}")

    return None


def _save_record(
    task_id: str,
    prompt: str,
    negative_prompt: str,
    seed: int,
    model: str,
    width: int,
    height: int,
    steps: int,
    guidance: float,
    generation_time: float,
    batch_total: int,
    batch_index: int,
    image_path: str,
    strength: Optional[float] = None,
):
    try:
        db = SessionLocal()
        record = ImageRecord(
            prompt=prompt,
            negative_prompt=negative_prompt,
            seed=seed,
            model=model,
            width=width,
            height=height,
            steps=steps,
            guidance=guidance,
            strength=strength or 0.0,
            image_path=image_path,
            generation_time=generation_time,
            batch_total=batch_total,
            batch_index=batch_index,
            task_id=task_id,
        )
        db.add(record)
        db.flush()
        record_id = record.id
        db.commit()
        db.close()
        log.info("task=%s record saved to DB (id=%s)", task_id[:8], record_id)
    except Exception as e:
        log.error("task=%s failed to save record: %s", task_id[:8], e)
