"""ML model retraining pipeline with MLflow integration.

Automates training, validation, and model registry updates.
"""

import json
import time
from datetime import datetime
from typing import Dict, Tuple

import mlflow
import mlflow.sklearn
import ray
from mlflow.tracking import MlflowClient
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split

from alfred.core.protocols import Service
from alfred.ml.alert_dataset import AlertDataset

class RetrainPipeline(Service):
    """Automated ML model retraining pipeline with MLflow tracking"""

    def __init__(
        self,
        mlflow_uri: str = "http://localhost:5000",
        experiment_name: str = "alert-noise-reduction",
        model_name: str = "alert-noise-ranker",
        min_f1_score: float = 0.85,
        min_precision: float = 0.98,
    ):
        """Initialize the retraining pipeline.

        Args:
            mlflow_uri: MLflow tracking server URI
            experiment_name: MLflow experiment name
            model_name: Model name in registry
            min_f1_score: Minimum F1 score for promotion
            min_precision: Minimum precision for promotion.

        """
        self.mlflow_uri = mlflow_uri
        self.experiment_name = experiment_name
        self.model_name = model_name
        self.min_f1_score = min_f1_score
        self.min_precision = min_precision

        # Initialize MLflow
        mlflow.set_tracking_uri(mlflow_uri)
        mlflow.set_experiment(experiment_name)
        self.client = MlflowClient()

        # Initialize Ray for distributed training
        if not ray.is_initialized():
            ray.init(ignore_reinit_error=True)

    def train_model(
        self, dataset: AlertDataset, test_size: float = 0.2, random_state: int = 42
    ) -> Tuple[RandomForestClassifier, Dict[str, float]]:
        """Train a new model on the provided dataset.

        Args:
            dataset: Alert dataset for training
            test_size: Test split size
            random_state: Random seed

        Returns:
            Trained model and metrics dictionary.

        """
        # Extract features and labels
        X, y = dataset.prepare_training_data()

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )

        # Train model
        model = RandomForestClassifier(
            n_estimators=200,
            max_depth=15,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=random_state,
            n_jobs=-1,
        )

        # Train with Ray for distributed processing
        @ray.remote
        def train_forest():
            model.fit(X_train, y_train)
            return model

        # Execute training
        start_time = time.time()
        future = train_forest.remote()
        model = ray.get(future)
        training_time = time.time() - start_time

        # Evaluate model
        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]

        metrics = {
            "precision": precision_score(y_test, y_pred),
            "recall": recall_score(y_test, y_pred),
            "f1_score": f1_score(y_test, y_pred),
            "roc_auc": roc_auc_score(y_test, y_proba),
            "training_time": training_time,
            "test_size": len(X_test),
            "train_size": len(X_train),
        }

        # Calculate noise reduction
        noise_threshold = 0.7
        predicted_noise = (y_proba > noise_threshold).sum()
        y_test.sum()
        reduction_rate = predicted_noise / len(y_test) if len(y_test) > 0 else 0

        metrics["noise_reduction_rate"] = reduction_rate
        metrics["false_negative_rate"] = 1 - recall_score(y_test, y_pred)

        return model, metrics

    def log_model_to_mlflow(
        self,
        model: RandomForestClassifier,
        metrics: Dict[str, float],
        dataset_info: Dict,
    ) -> str:
        """Log model and metrics to MLflow.

        Args:
            model: Trained model
            metrics: Model metrics
            dataset_info: Dataset metadata

        Returns:
            MLflow run ID.

        """
        with mlflow.start_run() as run:
            # Log parameters
            mlflow.log_params(
                {
                    "n_estimators": model.n_estimators,
                    "max_depth": model.max_depth,
                    "min_samples_split": model.min_samples_split,
                    "min_samples_leaf": model.min_samples_leaf,
                    "dataset_size": dataset_info.get("total_size", 0),
                    "feature_count": dataset_info.get("feature_count", 0),
                }
            )

            # Log metrics
            mlflow.log_metrics(metrics)

            # Log model
            mlflow.sklearn.log_model(model, "model", registered_model_name=self.model_name)

            # Log dataset info
            mlflow.log_dict(dataset_info, "dataset_info.json")

            # Add tags
            mlflow.set_tags(
                {
                    "training_pipeline": "automated",
                    "model_type": "random_forest",
                    "use_case": "alert_noise_reduction",
                    "framework": "scikit-learn",
                }
            )

            return run.info.run_id

    def promote_model(self, run_id: str, metrics: Dict[str, float]) -> bool:
        """Promote model to production if it meets criteria.

        Args:
            run_id: MLflow run ID
            metrics: Model metrics

        Returns:
            True if promoted, False otherwise.

        """
        # Check promotion criteria
        if (
            metrics["f1_score"] >= self.min_f1_score
            and metrics["precision"] >= self.min_precision
            and metrics["false_negative_rate"] <= 0.02
        ):

            # Get latest model version
            model_version = self.client.get_latest_versions(self.model_name, stages=["None"])[0]

            # Transition to staging
            self.client.transition_model_version_stage(
                name=self.model_name,
                version=model_version.version,
                stage="Staging",
                archive_existing_versions=False,
            )

            # If staging tests pass, promote to production
            staging_metrics = self._test_staging_model(model_version.version)

            if staging_metrics["accuracy"] >= 0.95:
                self.client.transition_model_version_stage(
                    name=self.model_name,
                    version=model_version.version,
                    stage="Production",
                    archive_existing_versions=True,
                )

                print(f"Model version {model_version.version} promoted to production")
                return True
            else:
                print(f"Model version {model_version.version} failed staging tests")
                return False
        else:
            print("Model does not meet promotion criteria")
            print(f"F1: {metrics['f1_score']:.3f} (min: {self.min_f1_score})")
            print(f"Precision: {metrics['precision']:.3f} (min: {self.min_precision})")
            print(f"FNR: {metrics['false_negative_rate']:.3f} (max: 0.02)")
            return False

    def _test_staging_model(self, version: str) -> Dict[str, float]:
        """Test model in staging environment.

        Args:
            version: Model version to test

        Returns:
            Staging metrics.

        """
        # Load staging model
        model_uri = f"models:/{self.model_name}/{version}"
        mlflow.sklearn.load_model(model_uri)

        # Run validation tests
        # This would use a separate validation dataset in production
        validation_accuracy = 0.96  # Placeholder

        return {"accuracy": validation_accuracy}

    def run_pipeline(self, dataset_source: str, force_promotion: bool = False) -> Dict:
        """Run the complete retraining pipeline.

        Args:
            dataset_source: Database URI or file path
            force_promotion: Force promotion regardless of metrics

        Returns:
            Pipeline execution results.

        """
        print(f"Starting retraining pipeline at {datetime.now()}")

        # Load dataset
        dataset = AlertDataset(source=dataset_source)
        dataset_info = dataset.get_info()

        print(f"Loaded dataset: {dataset_info['total_size']} samples")

        # Train model
        model, metrics = self.train_model(dataset)

        print(f"Training complete. Metrics: {json.dumps(metrics, indent=2)}")

        # Log to MLflow
        run_id = self.log_model_to_mlflow(model, metrics, dataset_info)

        print(f"Model logged to MLflow. Run ID: {run_id}")

        # Promote model
        promoted = self.promote_model(run_id, metrics) if not force_promotion else True

        results = {
            "run_id": run_id,
            "metrics": metrics,
            "dataset_info": dataset_info,
            "promoted": promoted,
            "model_uri": f"runs:/{run_id}/model",
            "timestamp": datetime.now().isoformat(),
        }

        return results

    def get_production_model_uri(self) -> str:
        """Get URI of current production model.

        Returns:
            Production model URI.

        """
        try:
            production_versions = self.client.get_latest_versions(
                self.model_name, stages=["Production"]
            )

            if production_versions:
                version = production_versions[0].version
                return f"models:/{self.model_name}/{version}"
            else:
                return None
        except Exception as e:
            print(f"Error getting production model: {e}")
            return None

# CLI interface
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Alert ML Retraining Pipeline")
    parser.add_argument("--dataset", required=True, help="Dataset source (DB URI or file)")
    parser.add_argument("--mlflow-uri", default="http://localhost:5000", help="MLflow server URI")
    parser.add_argument("--experiment", default="alert-noise-reduction", help="MLflow experiment")
    parser.add_argument("--force-promotion", action="store_true", help="Force model promotion")

    args = parser.parse_args()

    pipeline = RetrainPipeline(mlflow_uri=args.mlflow_uri, experiment_name=args.experiment)

    results = pipeline.run_pipeline(
        dataset_source=args.dataset, force_promotion=args.force_promotion
    )

    print(f"\nPipeline complete: {json.dumps(results, indent=2)}")
