"""Unit tests for workload CLI functionality."""

import subprocess
import time
from unittest.mock import MagicMock, patch

import pytest
import requests

class TestWorkloadCLI:
    """Test suite for synthetic workload CLI."""

    def test_workload_help(self):
        """Test that workload help displays correctly."""
        result = subprocess.run(
            ["go", "run", "./cmd/alfred", "workload", "--help"], capture_output=True, text=True
        )
        assert result.returncode == 0
        assert "Generate synthetic workload" in result.stdout
        assert "--rps" in result.stdout
        assert "--burst" in result.stdout
        assert "--duration" in result.stdout

    @patch("requests.get")
    def test_workload_rps_flag(self, mock_get):
        """Test RPS flag controls request rate."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Run workload for 2 seconds with 5 RPS
        cmd = [
            "go",
            "run",
            "./cmd/alfred",
            "workload",
            "--rps=5",
            "--duration=2s",
            "--endpoint=http://test.local",
            "--random=false",
        ]

        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True)
        elapsed = time.time() - start_time

        assert result.returncode == 0
        # Should complete in approximately 2 seconds
        assert 1.5 < elapsed < 3.0

    def test_workload_burst_flag(self):
        """Test burst flag functionality."""
        # This is a simplified test - in real implementation
        # we would mock HTTP calls and verify burst pattern
        cmd = [
            "go",
            "run",
            "./cmd/alfred",
            "workload",
            "--rps=1",
            "--burst=10",
            "--duration=1s",
            "--endpoint=http://test.local",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 0
        assert "burst" in result.stdout.lower()

    def test_random_query_mix(self):
        """Test random query mix functionality."""
        cmd = [
            "go",
            "run",
            "./cmd/alfred",
            "workload",
            "--rps=1",
            "--duration=1s",
            "--random=true",
            "--endpoint=http://test.local",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 0
        # Should use various endpoints from query templates

    def test_workload_metrics_output(self):
        """Test that workload outputs metrics summary."""
        cmd = [
            "go",
            "run",
            "./cmd/alfred",
            "workload",
            "--rps=1",
            "--duration=1s",
            "--endpoint=http://invalid.local",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        # Should still exit cleanly even with errors
        assert result.returncode == 0
        assert "Total=" in result.stdout
        assert "Success=" in result.stdout
        assert "Errors=" in result.stdout
        assert "Duration=" in result.stdout

@pytest.mark.integration
class TestWorkloadIntegration:
    """Integration tests for workload CLI."""

    def test_workload_against_real_endpoint(self):
        """Test workload against a real endpoint if available."""
        # Skip if no local service is running
        try:
            response = requests.get("http://localhost:8080/health", timeout=1)
            if response.status_code != 200:
                pytest.skip("No local service available")
        except Exception:
            pytest.skip("No local service available")

        cmd = [
            "go",
            "run",
            "./cmd/alfred",
            "workload",
            "--rps=10",
            "--duration=5s",
            "--endpoint=http://localhost:8080",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 0
        assert "success rate" in result.stdout.lower()
