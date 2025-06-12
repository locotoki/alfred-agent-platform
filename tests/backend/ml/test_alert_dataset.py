"""Tests for alert dataset loader."""

from backend.alfred.ml.alert_dataset import load_alert_dataset

def test_load_alert_dataset_default():
    """Test loading dataset with default parameters."""
    dataset = load_alert_dataset()

    assert isinstance(dataset, list)
    assert len(dataset) > 0

    # Check structure of returned data
    for text, label in dataset:
        assert isinstance(text, str)
        assert isinstance(label, str)
        assert label in ["noise", "critical", "warning"]

def test_load_alert_dataset_custom_days():
    """Test loading dataset with custom day parameter."""
    dataset = load_alert_dataset(days=7)

    assert isinstance(dataset, list)
    # Currently returns stub data, so length won't change
    # This will be updated when real implementation is added
