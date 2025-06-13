"""Alert Explainer Agent.

This module provides an agent that explains alerts in natural language by analyzing
alert metadata and providing actionable context.
"""

import re
from typing import Any, Dict, Optional, Union

import structlog
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from prometheus_client import Counter

# Import the LLM base class from our custom interface
# In practice, this would be properly typed
LLM = Any  # Placeholder for a proper LLM interface
# Set up metrics
explanations_total = Counter(
    "alfred_alert_explanations_total", "Total alert explanations generated", ["result"]
)

logger = structlog.get_logger(__name__)


class ExplainerAgent:
    """Agent for explaining alerts in natural language."""

    def __init__(self, llm: Optional[LLM] = None):
        """Initialize the agent with optional LLM configuration."""
        self.llm = llm
        self._chain: Optional[LLMChain] = None
        self._setup_chain()

    def _setup_chain(self) -> None:
        """Set up the LangChain for alert explanation."""
        if not self.llm:
            logger.warning("No LLM configured, using stub mode")
            return

        prompt = PromptTemplate(
            input_variables=["alert_name", "alert_details", "metric_value"],
            template="""
You are an expert Site Reliability Engineer. Generate a concise explanation for the following alert:

Alert: {alert_name}
Details: {alert_details}
Current Value: {metric_value}

Explain:
1. What this alert means in plain language
2. Potential causes of the alert
3. Suggested troubleshooting steps
4. Priority level (High, Medium, Low)

Be concise but informative.
""",
        )

        self._chain = LLMChain(llm=self.llm, prompt=prompt)
        logger.info("explainer_chain_initialized")

    async def explain_alert(self, alert_data: Dict[str, Any]) -> Dict[str, Union[str, bool]]:
        """Generate an explanation for an alert.

        Args:
            alert_data: Dictionary containing alert information

        Returns:
            Dictionary with explanation and metadata
        """
        # Extract alert information
        alert_name = alert_data.get("alert_name", "Unknown Alert")
        alert_details = alert_data.get("description", "No details provided")
        metric_value = alert_data.get("value", "Unknown")

        logger.info(
            "explaining_alert",
            alert_name=alert_name,
            has_details=bool(alert_details),
        )

        # Generate explanation
        explanation = ""

        try:
            if self._chain:
                # Use the LLM chain to generate the explanation
                # Since we're using a mock in tests, we don't actually need to await here
                # In real code with a real LLM, we'd use await self._chain.arun()
                if hasattr(self._chain, "arun"):
                    explanation = await self._chain.arun(
                        alert_name=alert_name,
                        alert_details=alert_details,
                        metric_value=metric_value,
                    )
                else:
                    # For backward compatibility with non-async chains
                    explanation = self._chain.run(
                        alert_name=alert_name,
                        alert_details=alert_details,
                        metric_value=metric_value,
                    )
                explanations_total.labels(result="success").inc()
            else:
                # Fallback static explanation when no LLM is configured
                explanation = self._generate_fallback_explanation(alert_name, alert_details)
                explanations_total.labels(result="fallback").inc()

            logger.info("explanation_generated", length=len(explanation))

            return {
                "explanation": explanation,
                "alert_name": alert_name,
                "success": True,
            }

        except Exception as e:
            logger.error(
                "explanation_error",
                error=str(e),
                error_type=type(e).__name__,
                alert_name=alert_name,
            )
            explanations_total.labels(result="error").inc()

            return {
                "explanation": f"Failed to generate explanation: {str(e)}",
                "alert_name": alert_name,
                "error": str(e),
                "success": False,
            }

    def _generate_fallback_explanation(self, alert_name: str, alert_details: str) -> str:
        """Generate a basic fallback explanation when LLM is unavailable.

        Args:
            alert_name: The name of the alert
            alert_details: Additional alert details

        Returns:
            A generic explanation based on alert patterns
        """
        # Simple pattern matching for common alert types
        explanation_parts = [
            f"Alert: {alert_name}",
            "",
            "This alert indicates a potential system issue that requires attention.",
        ]

        # Check for memory-related alerts
        if re.search(r"memory|ram|oom", alert_name.lower()):
            explanation_parts.extend(
                [
                    "",
                    "This appears to be a memory-related alert.",
                    "Potential causes:",
                    "- Memory leak in application",
                    "- Insufficient resources allocated",
                    "- Unexpected traffic spike",
                    "",
                    "Recommended actions:",
                    "- Check system memory usage",
                    "- Review recent deployments",
                    "- Consider scaling resources if needed",
                ]
            )
        # CPU alerts
        elif re.search(r"cpu|load|performance", alert_name.lower()):
            explanation_parts.extend(
                [
                    "",
                    "This appears to be a CPU/performance alert.",
                    "Potential causes:",
                    "- High computational load",
                    "- Inefficient code or queries",
                    "- Resource contention",
                    "",
                    "Recommended actions:",
                    "- Review system metrics",
                    "- Check for long-running processes",
                    "- Analyze recent code changes",
                ]
            )
        # Disk alerts
        elif re.search(r"disk|storage|volume", alert_name.lower()):
            explanation_parts.extend(
                [
                    "",
                    "This appears to be a disk/storage alert.",
                    "Potential causes:",
                    "- Running out of disk space",
                    "- High I/O operations",
                    "- Logs or temporary files accumulation",
                    "",
                    "Recommended actions:",
                    "- Check disk usage and growth patterns",
                    "- Review log rotation settings",
                    "- Clean unnecessary files or add capacity",
                ]
            )
        # Network alerts
        elif re.search(r"network|connect|latency|timeout", alert_name.lower()):
            explanation_parts.extend(
                [
                    "",
                    "This appears to be a network-related alert.",
                    "Potential causes:",
                    "- Network congestion",
                    "- Service unavailability",
                    "- DNS or routing issues",
                    "",
                    "Recommended actions:",
                    "- Verify network connectivity",
                    "- Check dependent service status",
                    "- Review recent network changes",
                ]
            )
        # Generic fallback
        else:
            explanation_parts.extend(
                [
                    "",
                    "Please investigate the system metrics and logs for more information.",
                    "",
                    "Priority: To be determined based on system impact",
                ]
            )

        return "\n".join(explanation_parts)
