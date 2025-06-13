"""Model registry management for ML models.

Handles model versioning, promotion, and deployment.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional

import mlflow
from mlflow.tracking import MlflowClient

from alfred.core.protocols import Service

class ModelRegistry(Service):
    """Manages ML model registry and lifecycle"""

    def __init__(
        self,
        mlflow_uri: str = "http://localhost:5000",
        model_name: str = "alert-noise-ranker",
    ):
        """Initialize model registry client.

        Args:
            mlflow_uri: MLflow tracking server URI
            model_name: Default model name.

        """
        self.mlflow_uri = mlflow_uri
        self.model_name = model_name

        mlflow.set_tracking_uri(mlflow_uri)
        self.client = MlflowClient()

    def register_model(
        self,
        run_id: str,
        artifact_path: str = "model",
        model_name: Optional[str] = None,
    ) -> str:
        """Register a model from an MLflow run.

        Args:
            run_id: MLflow run ID
            artifact_path: Path to model artifact in run
            model_name: Model name (uses default if None)

        Returns:
            Registered model version.

        """
        model_name = model_name or self.model_name
        model_uri = f"runs:/{run_id}/{artifact_path}"

        # Register model
        result = mlflow.register_model(model_uri, model_name)

        # Add metadata
        self.client.update_model_version(
            name=model_name,
            version=result.version,
            description=f"Model registered from run {run_id}",
        )

        return result.version

    def promote_model(
        self, version: str, stage: str = "Production", model_name: Optional[str] = None
    ) -> bool:
        """Promote model version to a stage.

        Args:
            version: Model version
            stage: Target stage (Staging/Production)
            model_name: Model name (uses default if None)

        Returns:
            Success status.

        """
        model_name = model_name or self.model_name

        try:
            # Archive existing versions in target stage
            if stage == "Production":
                archive_existing = True
            else:
                archive_existing = False

            self.client.transition_model_version_stage(
                name=model_name,
                version=version,
                stage=stage,
                archive_existing_versions=archive_existing,
            )

            # Add promotion metadata
            self.client.set_model_version_tag(
                name=model_name,
                version=version,
                key="promoted_at",
                value=datetime.now().isoformat(),
            )

            self.client.set_model_version_tag(
                name=model_name, version=version, key="promoted_to", value=stage
            )

            return True

        except Exception as e:
            print(f"Error promoting model: {e}")
            return False

    def get_latest_version(
        self, stage: str = "Production", model_name: Optional[str] = None
    ) -> Optional[Dict]:
        """Get latest model version for a stage.

        Args:
            stage: Model stage
            model_name: Model name (uses default if None)

        Returns:
            Model version info or None.

        """
        model_name = model_name or self.model_name

        try:
            versions = self.client.get_latest_versions(name=model_name, stages=[stage])

            if versions:
                version = versions[0]
                return {
                    "version": version.version,
                    "stage": version.current_stage,
                    "status": version.status,
                    "created_at": version.creation_timestamp,
                    "updated_at": version.last_updated_timestamp,
                    "run_id": version.run_id,
                    "model_uri": f"models:/{model_name}/{version.version}",
                    "tags": version.tags,
                }
            return None

        except Exception as e:
            print(f"Error getting latest version: {e}")
            return None

    def compare_versions(
        self, version1: str, version2: str, model_name: Optional[str] = None
    ) -> Dict:
        """Compare two model versions.

        Args:
            version1: First version
            version2: Second version
            model_name: Model name (uses default if None)

        Returns:
            Comparison results.

        """
        model_name = model_name or self.model_name

        v1_info = self.client.get_model_version(model_name, version1)
        v2_info = self.client.get_model_version(model_name, version2)

        # Get metrics from runs
        run1 = self.client.get_run(v1_info.run_id)
        run2 = self.client.get_run(v2_info.run_id)

        comparison = {
            "version1": {
                "version": version1,
                "stage": v1_info.current_stage,
                "metrics": run1.data.metrics,
                "params": run1.data.params,
            },
            "version2": {
                "version": version2,
                "stage": v2_info.current_stage,
                "metrics": run2.data.metrics,
                "params": run2.data.params,
            },
            "metric_diff": {},
        }

        # Calculate metric differences
        for metric in run1.data.metrics:
            if metric in run2.data.metrics:
                diff = run2.data.metrics[metric] - run1.data.metrics[metric]
                comparison["metric_diff"][metric] = {
                    "v1": run1.data.metrics[metric],
                    "v2": run2.data.metrics[metric],
                    "diff": diff,
                    "pct_change": (
                        (diff / run1.data.metrics[metric] * 100)
                        if run1.data.metrics[metric] != 0
                        else 0
                    ),
                }

        return comparison

    def rollback_production(self, model_name: Optional[str] = None) -> bool:
        """Rollback to previous production version.

        Args:
            model_name: Model name (uses default if None)

        Returns:
            Success status.

        """
        model_name = model_name or self.model_name

        try:
            # Get current and archived production versions
            all_versions = self.client.search_model_versions(f"name='{model_name}'")

            production_versions = [v for v in all_versions if v.current_stage == "Production"]
            archived_versions = [
                v
                for v in all_versions
                if v.current_stage == "Archived"
                and "promoted_to" in v.tags
                and v.tags["promoted_to"] == "Production"
            ]

            if not production_versions or not archived_versions:
                print("No versions available for rollback")
                return False

            # Archive current production
            current_prod = production_versions[0]
            self.client.transition_model_version_stage(
                name=model_name, version=current_prod.version, stage="Archived"
            )

            # Restore most recent archived production
            archived_versions.sort(key=lambda x: x.last_updated_timestamp, reverse=True)
            restore_version = archived_versions[0]

            self.client.transition_model_version_stage(
                name=model_name, version=restore_version.version, stage="Production"
            )

            # Log rollback
            self.client.set_model_version_tag(
                name=model_name,
                version=restore_version.version,
                key="rollback_at",
                value=datetime.now().isoformat(),
            )

            print(f"Rolled back from v{current_prod.version} to v{restore_version.version}")
            return True

        except Exception as e:
            print(f"Error during rollback: {e}")
            return False

    def get_model_lineage(self, model_name: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """Get model version history.

        Args:
            model_name: Model name (uses default if None)
            limit: Number of versions to return

        Returns:
            List of version info.

        """
        model_name = model_name or self.model_name

        versions = self.client.search_model_versions(
            f"name='{model_name}'",
            order_by=["creation_timestamp DESC"],
            max_results=limit,
        )

        lineage = []
        for v in versions:
            # Get run info
            run = self.client.get_run(v.run_id)

            lineage.append(
                {
                    "version": v.version,
                    "stage": v.current_stage,
                    "created_at": v.creation_timestamp,
                    "metrics": run.data.metrics,
                    "params": run.data.params,
                    "tags": v.tags,
                    "description": v.description,
                }
            )

        return lineage

    def export_model_metadata(self, version: str, model_name: Optional[str] = None) -> Dict:
        """Export complete model metadata.

        Args:
            version: Model version
            model_name: Model name (uses default if None)

        Returns:
            Model metadata dictionary.

        """
        model_name = model_name or self.model_name

        version_info = self.client.get_model_version(model_name, version)
        run = self.client.get_run(version_info.run_id)

        metadata = {
            "model_name": model_name,
            "version": version,
            "stage": version_info.current_stage,
            "created_at": version_info.creation_timestamp,
            "updated_at": version_info.last_updated_timestamp,
            "run_id": version_info.run_id,
            "artifact_uri": run.info.artifact_uri,
            "metrics": run.data.metrics,
            "params": run.data.params,
            "tags": {**run.data.tags, **version_info.tags},
            "model_uri": f"models:/{model_name}/{version}",
            "signature": None,
        }

        # Try to get model signature
        try:
            mlflow.sklearn.load_model(metadata["model_uri"])
            # Model signature would be extracted here if available
        except Exception:
            pass

        return metadata

# CLI interface for model registry operations
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Model Registry Management")
    parser.add_argument("--mlflow-uri", default="http://localhost:5000", help="MLflow server URI")
    parser.add_argument("--model-name", default="alert-noise-ranker", help="Model name")
    parser.add_argument(
        "--action",
        choices=["promote", "rollback", "compare", "lineage", "export"],
        required=True,
        help="Action to perform",
    )
    parser.add_argument("--version", help="Model version")
    parser.add_argument("--stage", default="Production", help="Target stage")
    parser.add_argument("--compare-with", help="Version to compare with")

    args = parser.parse_args()

    registry = ModelRegistry(args.mlflow_uri, args.model_name)

    if args.action == "promote":
        success = registry.promote_model(args.version, args.stage)
        print(f"Promotion {'successful' if success else 'failed'}")

    elif args.action == "rollback":
        success = registry.rollback_production()
        print(f"Rollback {'successful' if success else 'failed'}")

    elif args.action == "compare":
        comparison = registry.compare_versions(args.version, args.compare_with)
        print(json.dumps(comparison, indent=2))

    elif args.action == "lineage":
        lineage = registry.get_model_lineage()
        print(json.dumps(lineage, indent=2))

    elif args.action == "export":
        metadata = registry.export_model_metadata(args.version)
        print(json.dumps(metadata, indent=2))
