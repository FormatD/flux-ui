"""
Tests for Img2Img width/height parameter support (FOR-9).
Run: python -m pytest tests/test_img2img_width_height.py -v
"""
import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client with the FastAPI app."""
    from backend.app.main import app
    with TestClient(app) as c:
        yield c


class TestImg2ImgWidthHeight:
    """Verify Img2ImgRequest schema and route pass width/height correctly."""

    def test_schema_has_width_height_defaults(self):
        """Img2ImgRequest should have width=1024 and height=1024 defaults."""
        from backend.app.schemas.schemas import Img2ImgRequest
        req = Img2ImgRequest(prompt="test", image_path="/tmp/test.png")
        assert req.width == 1024
        assert req.height == 1024

    def test_schema_accepts_custom_width_height(self):
        """Img2ImgRequest should accept custom width/height."""
        from backend.app.schemas.schemas import Img2ImgRequest
        req = Img2ImgRequest(
            prompt="test",
            image_path="/tmp/test.png",
            width=768,
            height=512,
        )
        assert req.width == 768
        assert req.height == 512

    def test_route_rejects_missing_prompt(self, client):
        """POST /api/generate/img2img with empty prompt should 400."""
        resp = client.post("/api/generate/img2img", json={
            "prompt": "",
            "image_path": "/tmp/test.png",
        })
        assert resp.status_code == 400
        assert "Prompt" in resp.text

    def test_route_rejects_missing_image_path(self, client):
        """POST /api/generate/img2img without image_path should 400."""
        resp = client.post("/api/generate/img2img", json={
            "prompt": "test",
        })
        assert resp.status_code == 400
        assert "Image path" in resp.text

    def test_route_accepts_custom_width_height(self, client):
        """POST /api/generate/img2img with custom width/height should queue with those values."""
        resp = client.post("/api/generate/img2img", json={
            "prompt": "test image",
            "image_path": "/tmp/test.png",
            "width": 768,
            "height": 512,
            "steps": 2,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "task_id" in data
        assert data["status"] == "queued"

        # Fetch the task from the queue to verify params
        from backend.app.services.task_queue import task_queue
        task = task_queue.get_task(data["task_id"])
        assert task is not None
        params = task["data"]["params"]
        assert params["width"] == 768
        assert params["height"] == 512

    def test_route_defaults_width_height(self, client):
        """POST /api/generate/img2img without width/height should default to 1024."""
        resp = client.post("/api/generate/img2img", json={
            "prompt": "test image",
            "image_path": "/tmp/test.png",
            "steps": 2,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "task_id" in data

        # Fetch the task to verify defaults
        from backend.app.services.task_queue import task_queue
        task = task_queue.get_task(data["task_id"])
        assert task is not None
        params = task["data"]["params"]
        assert params["width"] == 1024
        assert params["height"] == 1024

    def test_route_seed_is_passed_through(self, client):
        """Seed should be passed through when explicitly provided."""
        resp = client.post("/api/generate/img2img", json={
            "prompt": "seed test",
            "image_path": "/tmp/test.png",
            "seed": 42,
            "steps": 2,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["seed"] == 42

    def test_route_random_seed_when_not_provided(self, client):
        """When no seed is provided, a random seed should be generated."""
        resp = client.post("/api/generate/img2img", json={
            "prompt": "random seed test",
            "image_path": "/tmp/test.png",
            "steps": 2,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["seed"] is not None
        assert isinstance(data["seed"], int)

    def test_route_all_params_in_task_data(self, client):
        """All img2img params should be passed through to the task data."""
        resp = client.post("/api/generate/img2img", json={
            "prompt": "comprehensive test",
            "negative_prompt": "bad stuff",
            "model": "test-model",
            "steps": 8,
            "guidance": 7.5,
            "seed": 12345,
            "strength": 0.6,
            "image_path": "/tmp/comprehensive.png",
            "width": 512,
            "height": 768,
        })
        assert resp.status_code == 200
        data = resp.json()

        from backend.app.services.task_queue import task_queue
        task = task_queue.get_task(data["task_id"])
        assert task is not None
        params = task["data"]["params"]
        assert params["prompt"] == "comprehensive test"
        assert params["negative_prompt"] == "bad stuff"
        assert params["model"] == "test-model"
        assert params["steps"] == 8
        assert params["guidance"] == 7.5
        assert params["seed"] == 12345
        assert params["strength"] == 0.6
        assert params["image_path"] == "/tmp/comprehensive.png"
        assert params["width"] == 512
        assert params["height"] == 768
