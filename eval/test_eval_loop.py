"""Evaluation loop test module."""

import pathlib

import yaml

DATASET = pathlib.Path(__file__).parent / "sample_dataset.yml"
def test_dataset_loads():
    """Test that the sample dataset loads correctly."""
    with open(DATASET) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, list)
