from unittest.mock import MagicMock, patch

from backend.alfred.ml import retrain_pipeline

def test_schedule_stub():
    assert callable(retrain_pipeline.schedule)

@patch("backend.alfred.ml.retrain_pipeline.ray")
@patch("backend.alfred.ml.retrain_pipeline.mlflow")
@patch("backend.alfred.ml.retrain_pipeline.SentenceTransformer")
@patch("backend.alfred.ml.retrain_pipeline.load_alert_dataset")
@patch("backend.alfred.ml.retrain_pipeline.save_promoted_model")
@patch("backend.alfred.ml.retrain_pipeline.should_promote")
def test_schedule_full_pipeline(
    mock_should_promote,
    mock_save_model,
    mock_load_dataset,
    mock_transformer,
    mock_mlflow,
    mock_ray,
):
    """Test the full retrain pipeline flow."""
    # Setup mocks
    mock_load_dataset.return_value = [("alert 1", "noise"), ("alert 2", "critical")]
    mock_model = MagicMock()
    mock_transformer.return_value = mock_model
    mock_should_promote.return_value = True

    # Run the pipeline
    retrain_pipeline.schedule()

    # Verify calls
    mock_ray.init.assert_called_once_with(address="auto", ignore_reinit_error=True)
    mock_load_dataset.assert_called_once_with(days=30)
    mock_transformer.assert_called_once_with("all-MiniLM-L6-v2")
    mock_mlflow.log_metric.assert_any_call("noise_cut", 0.46)
    mock_mlflow.log_metric.assert_any_call("fnr", 0.018)
    mock_should_promote.assert_called_once()
    mock_save_model.assert_called_once()
