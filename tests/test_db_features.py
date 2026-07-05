"""
Unit tests for SQLite WAL mode and write exception handling.
"""

import os
import sys
import sqlite3
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


# ================================================================
# Tests: WAL mode enabled in database.py
# ================================================================

def test_wal_pragma_executed_on_connect():
    """Verify that PRAGMA journal_mode=WAL is called on each new SQLite connection."""
    from app.database import _enable_sqlite_wal

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    _enable_sqlite_wal(mock_conn, None)

    mock_conn.cursor.assert_called_once()
    mock_cursor.execute.assert_called_once_with("PRAGMA journal_mode=WAL")
    mock_cursor.close.assert_called_once()


def test_wal_pragma_skipped_for_non_sqlite():
    """Verify WAL pragma is NOT executed for non-SQLite databases."""
    import app.database

    original_url = app.database.DATABASE_URL
    try:
        app.database.DATABASE_URL = "postgresql://localhost/test"

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        app.database._enable_sqlite_wal(mock_conn, None)

        mock_conn.cursor.assert_not_called()
    finally:
        app.database.DATABASE_URL = original_url


def test_wal_listener_importable():
    """Verify the _enable_sqlite_wal function exists and the event module is imported."""
    from app.database import _enable_sqlite_wal, event
    assert callable(_enable_sqlite_wal)
    assert event is not None


# ================================================================
# Tests: Retry logic in task_queue.py write functions
# ================================================================


def test_save_task_retries_on_operational_error():
    """_save_task_to_db retries up to 3 times on OperationalError, succeeds on 3rd."""
    from app.services.task_queue import _save_task_to_db

    mock_session = MagicMock()
    mock_session_instance = MagicMock()
    mock_session_instance.commit.side_effect = [
        sqlite3.OperationalError("database is locked"),
        sqlite3.OperationalError("database is locked"),
        None,
    ]
    mock_session.return_value = mock_session_instance

    with patch("app.services.task_queue.SessionLocal", mock_session):
        _save_task_to_db("test-id", {"type": "text2img", "params": {"prompt": "test"}}, "waiting")

    assert mock_session_instance.commit.call_count == 3
    assert mock_session_instance.close.call_count == 3
    assert mock_session.call_count == 3


def test_save_task_gives_up_after_3_operational_errors():
    """_save_task_to_db gives up after 3 consecutive OperationalErrors."""
    from app.services.task_queue import _save_task_to_db

    mock_session = MagicMock()
    mock_session_instance = MagicMock()
    mock_session_instance.commit.side_effect = (
        sqlite3.OperationalError("database is locked"),
        sqlite3.OperationalError("database is locked"),
        sqlite3.OperationalError("database is locked"),
    )
    mock_session.return_value = mock_session_instance

    with patch("app.services.task_queue.SessionLocal", mock_session):
        _save_task_to_db("test-id-2", {"type": "text2img", "params": {"prompt": "x"}}, "waiting")

    assert mock_session_instance.commit.call_count == 3
    assert mock_session.call_count == 3


def test_save_task_does_not_retry_non_operational_error():
    """_save_task_to_db does NOT retry on non-transient errors."""
    from app.services.task_queue import _save_task_to_db

    mock_session = MagicMock()
    mock_session_instance = MagicMock()
    mock_session_instance.commit.side_effect = RuntimeError("unexpected error")
    mock_session.return_value = mock_session_instance

    with patch("app.services.task_queue.SessionLocal", mock_session):
        _save_task_to_db("test-id-3", {"type": "text2img", "params": {}}, "waiting")

    assert mock_session_instance.commit.call_count == 1
    assert mock_session.call_count == 1


def test_update_task_status_retries_on_operational_error():
    """_update_task_status retries up to 3 times on OperationalError."""
    from app.services.task_queue import _update_task_status

    mock_session = MagicMock()
    mock_session_instance = MagicMock()
    mock_record = MagicMock()
    mock_session_instance.query.return_value.filter.return_value.first.return_value = mock_record
    mock_session_instance.commit.side_effect = [
        sqlite3.OperationalError("database is locked"),
        None,
    ]
    mock_session.return_value = mock_session_instance

    with patch("app.services.task_queue.SessionLocal", mock_session):
        _update_task_status("test-id", "running")

    assert mock_session_instance.commit.call_count == 2
    assert mock_session.call_count == 2
    assert mock_record.status == "running"


def test_update_task_status_gives_up_after_3_errors():
    """_update_task_status gives up after 3 OperationalErrors."""
    from app.services.task_queue import _update_task_status

    mock_session = MagicMock()
    mock_session_instance = MagicMock()
    mock_record = MagicMock()
    mock_session_instance.query.return_value.filter.return_value.first.return_value = mock_record
    mock_session_instance.commit.side_effect = (
        sqlite3.OperationalError("database is locked"),
        sqlite3.OperationalError("database is locked"),
        sqlite3.OperationalError("database is locked"),
    )
    mock_session.return_value = mock_session_instance

    with patch("app.services.task_queue.SessionLocal", mock_session):
        _update_task_status("test-id", "failed")

    assert mock_session_instance.commit.call_count == 3
    assert mock_session.call_count == 3


def test_update_task_status_does_not_retry_non_operational():
    """_update_task_status does NOT retry on non-transient errors."""
    from app.services.task_queue import _update_task_status

    mock_session = MagicMock()
    mock_session_instance = MagicMock()
    mock_session_instance.commit.side_effect = ValueError("bad value")
    mock_session.return_value = mock_session_instance

    with patch("app.services.task_queue.SessionLocal", mock_session):
        _update_task_status("test-id", "completed")

    assert mock_session_instance.commit.call_count == 1
    assert mock_session.call_count == 1


def test_update_task_status_sets_error():
    """_update_task_status sets error field when provided."""
    from app.services.task_queue import _update_task_status

    mock_session = MagicMock()
    mock_session_instance = MagicMock()
    mock_record = MagicMock()
    mock_session_instance.query.return_value.filter.return_value.first.return_value = mock_record
    mock_session_instance.commit.side_effect = [None]
    mock_session.return_value = mock_session_instance

    with patch("app.services.task_queue.SessionLocal", mock_session):
        _update_task_status("test-id", "failed", error="out of memory")

    assert mock_record.status == "failed"
    assert mock_record.error == "out of memory"
    assert mock_session_instance.commit.call_count == 1


def test_update_task_status_sets_result_path():
    """_update_task_status sets result_path when provided."""
    from app.services.task_queue import _update_task_status

    mock_session = MagicMock()
    mock_session_instance = MagicMock()
    mock_record = MagicMock()
    mock_session_instance.query.return_value.filter.return_value.first.return_value = mock_record
    mock_session_instance.commit.side_effect = [None]
    mock_session.return_value = mock_session_instance

    with patch("app.services.task_queue.SessionLocal", mock_session):
        _update_task_status("test-id", "completed", result_path="/output/test.png")

    assert mock_record.status == "completed"
    assert mock_record.result_path == "/output/test.png"
    assert mock_session_instance.commit.call_count == 1
