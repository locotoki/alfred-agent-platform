"""Unit tests for the ExplainerAgent."""

import json
from pathlib import Path
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional
from unittest.mock import Mock, patch

import pytest
from langchain.chains import LLMChain
from langchain.schema import Generation, LLMResult
from langchain.schema.runnable import Runnable

from alfred.alerts.explainer.agent import ExplainerAgent

@pytest.fixture
def alert_payload():
    """Load the alert fixture."""
    # test file is at tests/unit/alfred/alerts/explainer/test_agent.py
    # fixture is at tests/fixtures/alerts/alert_critical.json
    # so we need to go up to tests/ and then down to fixtures/
    fixture_path = Path(__file__).parents[4] / "fixtures/alerts/alert_critical.json"
    with open(fixture_path, "r") as f:
        # Load and ensure we have the correct key for alert_name
        data = json.load(f)
        data["alert_name"] = data.get("alertname", "test_alert")
        return data

@pytest.fixture
def stub_agent():
    """Create a stub ExplainerAgent."""
    return ExplainerAgent()  # No LLM, uses stub mode

@pytest.fixture
def mock_llm():
    """Create a mock LLM that implements the Runnable interface."""

    class MockLLM(Runnable):
        def invoke(self, input: Any, config: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Any:
            return "Mocked LLM response"

        async def ainvoke(
            self, input: Any, config: Optional[Dict[str, Any]] = None, **kwargs: Any
        ) -> Any:
            return "Mocked LLM response"

        def batch(
            self, inputs: List[Any], config: Optional[Dict[str, Any]] = None, **kwargs: Any
        ) -> List[Any]:
            return ["Mocked LLM response"] * len(inputs)

        async def abatch(
            self, inputs: List[Any], config: Optional[Dict[str, Any]] = None, **kwargs: Any
        ) -> List[Any]:
            return ["Mocked LLM response"] * len(inputs)

        def stream(
            self, input: Any, config: Optional[Dict[str, Any]] = None, **kwargs: Any
        ) -> Iterator[Any]:
            yield "Mocked LLM response"

        async def astream(
            self, input: Any, config: Optional[Dict[str, Any]] = None, **kwargs: Any
        ) -> AsyncIterator[Any]:
            yield "Mocked LLM response"

        def generate(self, *args: Any, **kwargs: Any) -> LLMResult:
            return LLMResult(generations=[[Generation(text="Mocked LLM response")]])

        async def agenerate(self, *args: Any, **kwargs: Any) -> LLMResult:
            return LLMResult(generations=[[Generation(text="Mocked LLM response")]])

        def predict(self, *args: Any, **kwargs: Any) -> str:
            return "Mocked LLM response"

        async def apredict(self, *args: Any, **kwargs: Any) -> str:
            return "Mocked LLM response"

    return MockLLM()

def test_explainer_agent_initialization():
    """Test agent initialization."""
    agent = ExplainerAgent()
    assert agent.llm is None
    assert agent._chain is None

def test_explainer_agent_with_llm():
    """Test agent initialization with LLM."""
    with patch("alfred.alerts.explainer.agent.LLMChain") as MockLLMChain:
        # Create a mock chain with the necessary attributes
        mock_chain = Mock(spec=["run", "arun"])
        MockLLMChain.return_value = mock_chain

        # Create a mock LLM
        mock_llm = Mock(spec=["invoke", "predict", "ainvoke", "apredict"])

        # Initialize the agent with the mock LLM
        agent = ExplainerAgent(llm=mock_llm)

        # Verify the agent is configured correctly
        assert agent.llm == mock_llm
        assert agent._chain is not None

        # Verify the LLMChain was created with the correct parameters
        # We can't check the exact prompt since it's an implementation detail
        MockLLMChain.assert_called_once()
        args, kwargs = MockLLMChain.call_args
        assert kwargs["llm"] == mock_llm
        assert "prompt" in kwargs

async def test_explain_alert_stub_mode(stub_agent, alert_payload):
    """Test alert explanation in stub mode."""
    result = await stub_agent.explain_alert(alert_payload)

    assert result["success"] is True
    assert result["alert_name"] == alert_payload["alert_name"]
    assert "alert indicates" in result["explanation"].lower()
    assert "This alert" in result["explanation"]
    assert "Priority:" in result["explanation"]

async def test_explain_alert_missing_fields(stub_agent):
    """Test explanation with missing alert fields."""
    minimal_alert = {"alert_name": "TestAlert"}
    result = await stub_agent.explain_alert(minimal_alert)

    assert result["success"] is True
    assert result["alert_name"] == "TestAlert"
    assert isinstance(result["explanation"], str)
    assert len(result["explanation"]) > 0

@patch.object(LLMChain, "arun")
async def test_explain_alert_with_llm_success(mock_arun, mock_llm, alert_payload):
    """Test successful explanation with LLM."""
    expected_explanation = """Explanation: Service is down
Potential Causes: Network issues, process crashed
Remediation: Restart the service
Runbook: https://runbooks.alfred.ai/service-down"""

    # Set up the mock to return the expected explanation
    mock_arun.return_value = expected_explanation

    agent = ExplainerAgent(llm=mock_llm)
    result = await agent.explain_alert(alert_payload)

    assert result["success"] is True
    assert result["alert_name"] == alert_payload["alert_name"]
    assert result["explanation"] == expected_explanation

    # Verify the chain was called with the correct parameters
    mock_arun.assert_called_once_with(
        alert_name=alert_payload["alert_name"],
        alert_details=alert_payload["description"],
        metric_value=alert_payload["value"],
    )

@patch.object(LLMChain, "arun")
async def test_explain_alert_with_llm_failure(mock_arun, mock_llm, alert_payload):
    """Test explanation failure with LLM."""
    # Set up the mock to raise an exception
    mock_arun.side_effect = Exception("LLM error")

    agent = ExplainerAgent(llm=mock_llm)
    result = await agent.explain_alert(alert_payload)

    assert result["success"] is False
    assert result["alert_name"] == alert_payload["alert_name"]
    assert "Failed to generate explanation" in result["explanation"]
    assert "LLM error" in result["explanation"]
