"""Tests for MLflow model registry."""

from unittest.mock import Mock, patch

import pytest

from backend.alfred.ml.model_registry import ModelRegistry

class TestModelRegistry:
    """Test model registry functionality."""

    @pytest.fixture
    def mock_mlflow_client(self):
        """Mock MLflow client."""
        with patch("backend.alfred.ml.model_registry.MlflowClient") as mock:
            yield mock

    @pytest.fixture
    def registry(self, mock_mlflow_client):
        """Create registry instance."""
        return ModelRegistry(mlflow_uri="http://test:5000", model_name="test-model")

    def test_initialization(self, registry):
        """Test registry initialization."""
        assert registry.mlflow_uri == "http://test:5000"
        assert registry.model_name == "test-model"
        assert registry.client is not None

    def test_register_model(self, registry, mock_mlflow_client):
        """Test model registration."""
        mock_result = Mock()
        mock_result.version = "1"

        with patch("backend.alfred.ml.model_registry.mlflow.register_model") as mock_register:
            mock_register.return_value = mock_result

            version = registry.register_model(run_id="test-run-123", artifact_path="model")

            assert version == "1"
            mock_register.assert_called_once_with("runs:/test-run-123/model", "test-model")

    def test_promote_model_to_production(self, registry):
        """Test promoting model to production."""
        success = registry.promote_model(version="2", stage="Production")

        assert success
        registry.client.transition_model_version_stage.assert_called_once_with(
            name="test-model",
            version="2",
            stage="Production",
            archive_existing_versions=True,
        )

    def test_promote_model_to_staging(self, registry):
        """Test promoting model to staging."""
        success = registry.promote_model(version="3", stage="Staging")

        assert success
        registry.client.transition_model_version_stage.assert_called_once_with(
            name="test-model",
            version="3",
            stage="Staging",
            archive_existing_versions=False,
        )

    def test_promote_model_error(self, registry):
        """Test promotion error handling."""
        registry.client.transition_model_version_stage.side_effect = Exception("Test error")

        success = registry.promote_model(version="4", stage="Production")

        assert not success

    def test_get_latest_version(self, registry):
        """Test getting latest version."""
        mock_version = Mock()
        mock_version.version = "5"
        mock_version.current_stage = "Production"
        mock_version.status = "READY"
        mock_version.creation_timestamp = 1234567890
        mock_version.last_updated_timestamp = 1234567900
        mock_version.run_id = "run-456"
        mock_version.tags = {"env": "prod"}

        registry.client.get_latest_versions.return_value = [mock_version]

        result = registry.get_latest_version(stage="Production")

        assert result is not None
        assert result["version"] == "5"
        assert result["stage"] == "Production"
        assert result["model_uri"] == "models:/test-model/5"
        assert result["tags"] == {"env": "prod"}

    def test_get_latest_version_none(self, registry):
        """Test when no version exists."""
        registry.client.get_latest_versions.return_value = []

        result = registry.get_latest_version(stage="Production")

        assert result is None

    def test_compare_versions(self, registry):
        """Test version comparison."""
        # Mock version info
        v1_info = Mock()
        v1_info.run_id = "run-1"
        v1_info.current_stage = "Production"

        v2_info = Mock()
        v2_info.run_id = "run-2"
        v2_info.current_stage = "Staging"

        registry.client.get_model_version.side_effect = [v1_info, v2_info]

        # Mock run info
        run1 = Mock()
        run1.data.metrics = {"accuracy": 0.95, "f1": 0.90}
        run1.data.params = {"n_estimators": "100"}

        run2 = Mock()
        run2.data.metrics = {"accuracy": 0.97, "f1": 0.92}
        run2.data.params = {"n_estimators": "200"}

        registry.client.get_run.side_effect = [run1, run2]

        comparison = registry.compare_versions("1", "2")

        assert comparison["version1"]["version"] == "1"
        assert comparison["version2"]["version"] == "2"
        assert comparison["metric_diff"]["accuracy"]["diff"] == 0.02
        assert comparison["metric_diff"]["f1"]["pct_change"] == pytest.approx(2.22, rel=1e-2)

    def test_rollback_production(self, registry):
        """Test production rollback."""
        # Mock current production
        current_prod = Mock()
        current_prod.version = "3"
        current_prod.current_stage = "Production"

        # Mock archived version
        archived = Mock()
        archived.version = "2"
        archived.current_stage = "Archived"
        archived.tags = {"promoted_to": "Production"}
        archived.last_updated_timestamp = 1234567890

        # Mock search results
        all_versions = [current_prod, archived]
        registry.client.search_model_versions.return_value = all_versions

        success = registry.rollback_production()

        assert success

        # Verify current prod was archived
        assert registry.client.transition_model_version_stage.call_count == 2
        calls = registry.client.transition_model_version_stage.call_args_list

        # First call archives current
        assert calls[0].kwargs["name"] == "test-model"
        assert calls[0].kwargs["version"] == "3"
        assert calls[0].kwargs["stage"] == "Archived"

        # Second call restores previous
        assert calls[1].kwargs["name"] == "test-model"
        assert calls[1].kwargs["version"] == "2"
        assert calls[1].kwargs["stage"] == "Production"

    def test_get_model_lineage(self, registry):
        """Test getting model lineage."""
        # Mock versions
        versions = []
        for i in range(3):
            v = Mock()
            v.version = str(i + 1)
            v.current_stage = ["Production", "Staging", "Archived"][i]
            v.creation_timestamp = 1234567890 + i * 100
            v.tags = {"test": f"v{i+1}"}
            v.description = f"Version {i+1}"
            v.run_id = f"run-{i+1}"
            versions.append(v)

        registry.client.search_model_versions.return_value = versions

        # Mock runs
        def mock_get_run(run_id):
            run = Mock()
            run.data.metrics = {"accuracy": 0.95 + int(run_id.split("-")[1]) * 0.01}
            run.data.params = {"n_estimators": str(100 + int(run_id.split("-")[1]) * 50)}
            return run

        registry.client.get_run.side_effect = mock_get_run

        lineage = registry.get_model_lineage(limit=3)

        assert len(lineage) == 3
        assert lineage[0]["version"] == "1"
        assert lineage[0]["stage"] == "Production"
        assert lineage[0]["metrics"]["accuracy"] == 0.96

    def test_export_model_metadata(self, registry):
        """Test metadata export."""
        # Mock version info
        version_info = Mock()
        version_info.version = "4"
        version_info.current_stage = "Production"
        version_info.creation_timestamp = 1234567890
        version_info.last_updated_timestamp = 1234567900
        version_info.run_id = "run-789"
        version_info.tags = {"env": "prod"}

        registry.client.get_model_version.return_value = version_info

        # Mock run info
        run = Mock()
        run.info.artifact_uri = "s3://bucket/path"
        run.data.metrics = {"accuracy": 0.98}
        run.data.params = {"depth": "10"}
        run.data.tags = {"user": "test"}

        registry.client.get_run.return_value = run

        metadata = registry.export_model_metadata("4")

        assert metadata["model_name"] == "test-model"
        assert metadata["version"] == "4"
        assert metadata["stage"] == "Production"
        assert metadata["metrics"]["accuracy"] == 0.98
        assert metadata["model_uri"] == "models:/test-model/4"
        assert "env" in metadata["tags"]
        assert "user" in metadata["tags"]
