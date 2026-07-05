"""Tests for WebSocket heartbeat and connection management."""

import json
import time
from fastapi.testclient import TestClient

from app.main import app


def test_websocket_connect_and_ping_pong():
    """Test basic WebSocket ping/pong exchange."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "ping"})
            data = ws.receive_json()
            assert data == {"type": "pong"}


def test_websocket_multiple_ping_pong():
    """Test multiple ping/pong exchanges work correctly."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            for _ in range(3):
                ws.send_json({"type": "ping"})
                data = ws.receive_json()
                assert data == {"type": "pong"}


def test_websocket_subscribe_no_response():
    """Test that subscribe message does not break heartbeat tracking."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "subscribe"})
            # Subscribe should not produce a response,
            # but subsequent ping should still get pong
            ws.send_json({"type": "ping"})
            data = ws.receive_json()
            assert data == {"type": "pong"}


def test_websocket_client_pong():
    """Test that sending a pong updates the server's heartbeat tracker."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            # Send pong (response to a server ping we didn't receive yet)
            ws.send_json({"type": "pong"})
            # No immediate response, but it should keep the connection alive
            # Verify ping still works after
            ws.send_json({"type": "ping"})
            data = ws.receive_json()
            assert data == {"type": "pong"}


def test_websocket_disconnect_cleanup():
    """Test that disconnect cleans up the heartbeat task."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "ping"})
            data = ws.receive_json()
            assert data == {"type": "pong"}
        # Connection closed - heartbeat task should be cancelled
        # If not, pytest will hang or show errors
