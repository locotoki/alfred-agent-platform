"""Tests for database-backed alert dataset loader."""

import tempfile
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, text

from backend.alfred.config.settings import settings
from backend.alfred.ml.alert_dataset import (
    
,
    _severity_to_label,
    _strip_pii,
    load_alert_dataset,
)

@pytest.fixture
def test_db():
    """Create a temporary SQLite database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        engine = create_engine(f"sqlite:///{tmp.name}")

        # Create alerts table
        with engine.connect() as conn:
            conn.execute(
                text(
                    """
                CREATE TABLE alerts (
                    id INTEGER PRIMARY KEY,
                    message TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL
                ).
            """
                )
            )
            conn.commit()

            # Insert test data
            base_date = datetime.utcnow()
            test_data = [
                ("API timeout in service user@example.com", "error", base_date),
                (
                    "Memory usage at 192.168.1.1 exceeded 90%",
                    "warning",
                    base_date - timedelta(days=1),
                ),
                (
                    "Database connection from 10.0.0.1 failed",
                    "critical",
                    base_date - timedelta(days=2),
                ),
                (
                    "Debug log entry 555-123-4567",
                    "debug",
                    base_date - timedelta(days=5),
                ),
                ("Info: Deployment successful", "info", base_date - timedelta(days=10)),
                (
                    "Old alert",
                    "warning",
                    base_date - timedelta(days=40),
                ),  # Outside range
            ]

            for message, severity, created_at in test_data:
                conn.execute(
                    text(
                        "INSERT INTO alerts (message, severity, created_at) VALUES (:message, :severity, :created_at)"  # noqa: E501
                    ),
                    {
                        "message": message,
                        "severity": severity,
                        "created_at": created_at,
                    },
                )
            conn.commit()

        yield f"sqlite:///{tmp.name}"

def test_load_alert_dataset(test_db, monkeypatch):
    """Test loading alerts from database."""
    # Patch the settings to use test database
    monkeypatch.setattr(settings, "ALERT_DB_URI", test_db)

    # Load alerts from last 30 days
    dataset = load_alert_dataset(days=30)

    # Should get 5 alerts (excluding the one older than 30 days)
    assert len(dataset) == 5

    # Check that results are tuples of (message, label)
    for message, label in dataset:
        assert isinstance(message, str)
        assert isinstance(label, str)
        assert label in ["critical", "warning", "noise"]

    # Verify PII was stripped
    messages = [msg for msg, _ in dataset]
    assert not any("user@example.com" in msg for msg in messages)
    assert not any("192.168.1.1" in msg for msg in messages)
    assert not any("555-123-4567" in msg for msg in messages)

def test_load_alert_dataset_custom_days(test_db, monkeypatch):
    """Test loading alerts with custom day range."""
    monkeypatch.setattr(settings, "ALERT_DB_URI", test_db)

    # Load only last 3 days
    dataset = load_alert_dataset(days=3)

    # Should get 3 alerts
    assert len(dataset) == 3

def test_strip_pii():
    """Test PII stripping function."""
    test_cases = [
        ("Error from user@example.com", "Error from [EMAIL]"),
        ("Connection from 192.168.1.1 failed", "Connection from [IP] failed"),
        ("Contact support at 555-123-4567", "Contact support at [PHONE]"),
        ("Multiple PII: user@test.com at 10.0.0.1", "Multiple PII: [EMAIL] at [IP]"),
        ("No PII here", "No PII here"),
    ]

    for input_msg, expected in test_cases:
        assert _strip_pii(input_msg) == expected

def test_severity_to_label():
    """Test severity to label mapping."""
    test_cases = [
        ("critical", "critical"),
        ("CRITICAL", "critical"),
        ("error", "critical"),
        ("warning", "warning"),
        ("info", "noise"),
        ("debug", "noise"),
        ("unknown", "noise"),  # Default case
    ]

    for severity, expected_label in test_cases:
        assert _severity_to_label(severity) == expected_label
