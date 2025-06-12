"""Tests for the dynamic threshold optimization service."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from alfred.ml.thresholds import ThresholdConfig, ThresholdService

class TestThresholdConfig:
    """Test ThresholdConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ThresholdConfig()
        assert config.noise_threshold == 0.7
        assert config.confidence_min == 0.85
        assert config.batch_size == 100
        assert config.learning_rate == 0.01

    def test_to_dict(self):
        """Test conversion to dictionary."""
        config = ThresholdConfig(noise_threshold=0.8)
        data = config.to_dict()
        assert data["noise_threshold"] == 0.8
        assert data["confidence_min"] == 0.85
        assert len(data) == 4

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "noise_threshold": 0.9,
            "confidence_min": 0.95,
            "batch_size": 50,
            "learning_rate": 0.001,
        }
        config = ThresholdConfig.from_dict(data)
        assert config.noise_threshold == 0.9
        assert config.confidence_min == 0.95
        assert config.batch_size == 50
        assert config.learning_rate == 0.001

class TestThresholdService:
    """Test ThresholdService functionality."""

    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary config file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(
                {
                    "noise_threshold": 0.75,
                    "confidence_min": 0.9,
                    "batch_size": 200,
                    "learning_rate": 0.005,
                },
                f,
            )
            return Path(f.name)

    @pytest.fixture
    def metrics_mock(self):
        """Create a mock metrics collector."""
        return Mock()

    def test_initialization_with_file(self, temp_config_file, metrics_mock):
        """Test service initialization with existing config file."""
        service = ThresholdService(metrics=metrics_mock, config_path=str(temp_config_file))

        config = service.get_thresholds()
        assert config["noise_threshold"] == 0.75
        assert config["confidence_min"] == 0.9

        # Cleanup
        temp_config_file.unlink()

    def test_initialization_without_file(self, metrics_mock):
        """Test service initialization without config file."""
        service = ThresholdService(metrics=metrics_mock, config_path="/nonexistent/path.json")

        config = service.get_thresholds()
        assert config["noise_threshold"] == 0.7  # Default
        assert config["confidence_min"] == 0.85  # Default

    def test_get_thresholds(self, metrics_mock):
        """Test getting current thresholds."""
        service = ThresholdService(metrics=metrics_mock)
        thresholds = service.get_thresholds()

        assert isinstance(thresholds, dict)
        assert "noise_threshold" in thresholds
        assert "confidence_min" in thresholds
        assert "batch_size" in thresholds
        assert "learning_rate" in thresholds

    def test_update_thresholds_valid(self, temp_config_file, metrics_mock):
        """Test updating thresholds with valid values."""
        service = ThresholdService(metrics=metrics_mock, config_path=str(temp_config_file))

        updates = {"noise_threshold": 0.85, "batch_size": 150}

        result = service.update_thresholds(updates)

        assert result["noise_threshold"] == 0.85
        assert result["batch_size"] == 150
        assert result["confidence_min"] == 0.9  # Unchanged

        # Verify metrics were tracked
        metrics_mock.gauge.assert_any_call("threshold.noise_threshold", 0.85)
        metrics_mock.gauge.assert_any_call("threshold.batch_size", 150)

        # Cleanup
        temp_config_file.unlink()

    def test_update_thresholds_invalid_key(self, metrics_mock):
        """Test updating thresholds with invalid key."""
        service = ThresholdService(metrics=metrics_mock)

        with pytest.raises(ValueError, match="Invalid threshold keys"):
            service.update_thresholds({"invalid_key": 0.5})

    def test_save_config_error_handling(self, metrics_mock):
        """Test error handling when saving config fails."""
        with patch("builtins.open", side_effect=PermissionError("No write access")):
            service = ThresholdService(metrics=metrics_mock, config_path="/readonly/config.json")

            # Should not raise, but should track error
            service._save_config()

            metrics_mock.increment.assert_called_once()
            call_args = metrics_mock.increment.call_args
            assert call_args[0][0] == "threshold.save_error"

    def test_optimize_thresholds_high_false_positives(self, metrics_mock):
        """Test threshold optimization with high false positive rate."""
        service = ThresholdService(metrics=metrics_mock)

        # Initial state
        initial = service.get_thresholds()
        initial_noise = initial["noise_threshold"]

        # Optimize with high false positive rate
        performance_metrics = {"false_positive_rate": 0.15}
        optimized = service.optimize_thresholds(performance_metrics)

        # Should increase noise threshold
        assert optimized["noise_threshold"] > initial_noise
        assert optimized["noise_threshold"] <= 0.95  # Max cap

    def test_optimize_thresholds_low_false_positives(self, metrics_mock):
        """Test threshold optimization with low false positive rate."""
        service = ThresholdService(metrics=metrics_mock)

        # Initial state
        initial = service.get_thresholds()
        initial_noise = initial["noise_threshold"]

        # Optimize with low false positive rate
        performance_metrics = {"false_positive_rate": 0.03}
        optimized = service.optimize_thresholds(performance_metrics)

        # Should decrease noise threshold
        assert optimized["noise_threshold"] < initial_noise
        assert optimized["noise_threshold"] >= 0.5  # Min cap

    def test_optimize_thresholds_low_accuracy(self, metrics_mock):
        """Test threshold optimization with low accuracy."""
        service = ThresholdService(metrics=metrics_mock)

        # Initial state
        initial = service.get_thresholds()
        initial_confidence = initial["confidence_min"]

        # Optimize with low accuracy
        performance_metrics = {"accuracy": 0.85}
        optimized = service.optimize_thresholds(performance_metrics)

        # Should increase confidence minimum
        assert optimized["confidence_min"] > initial_confidence
        assert optimized["confidence_min"] <= 0.95  # Max cap

    def test_optimize_thresholds_high_accuracy(self, metrics_mock):
        """Test threshold optimization with high accuracy."""
        service = ThresholdService(metrics=metrics_mock)

        # Initial state
        initial = service.get_thresholds()
        initial_confidence = initial["confidence_min"]

        # Optimize with high accuracy
        performance_metrics = {"accuracy": 0.97}
        optimized = service.optimize_thresholds(performance_metrics)

        # Should decrease confidence minimum
        assert optimized["confidence_min"] < initial_confidence
        assert optimized["confidence_min"] >= 0.7  # Min cap

    def test_optimize_thresholds_combined_metrics(self, temp_config_file, metrics_mock):
        """Test optimization with multiple performance metrics."""
        service = ThresholdService(metrics=metrics_mock, config_path=str(temp_config_file))

        performance_metrics = {"false_positive_rate": 0.12, "accuracy": 0.88}

        optimized = service.optimize_thresholds(performance_metrics)

        # Both thresholds should be adjusted
        assert optimized["noise_threshold"] > 0.75  # Increased from initial
        assert optimized["confidence_min"] > 0.9  # Increased from initial

        # Config should be saved
        with open(temp_config_file) as f:
            saved_config = json.load(f)
            assert saved_config["noise_threshold"] == optimized["noise_threshold"]

        # Cleanup
        temp_config_file.unlink()

    def test_edge_cases(self, metrics_mock):
        """Test edge cases in threshold optimization."""
        service = ThresholdService(metrics=metrics_mock)

        # Already at max noise threshold
        service._config.noise_threshold = 0.95
        performance_metrics = {"false_positive_rate": 0.2}
        optimized = service.optimize_thresholds(performance_metrics)
        assert optimized["noise_threshold"] == 0.95  # Can't go higher

        # Already at min noise threshold
        service._config.noise_threshold = 0.5
        performance_metrics = {"false_positive_rate": 0.01}
        optimized = service.optimize_thresholds(performance_metrics)
        assert optimized["noise_threshold"] == 0.5  # Can't go lower
