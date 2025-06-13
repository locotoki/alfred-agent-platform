"""Configuration settings for the remediation system.

This module provides configurable settings for the remediation system, allowing for
environment-based configuration.
"""

import os
from typing import Any, Dict

# Maximum number of retry attempts for service remediation
# Can be overridden with REMEDIATION_MAX_RETRIES environment variable
MAX_RETRIES = int(os.environ.get("REMEDIATION_MAX_RETRIES", "3"))
# Default wait time between restart and health probe (in seconds)
# Can be overridden with REMEDIATION_WAIT_SECONDS environment variable
DEFAULT_WAIT_SECONDS = int(os.environ.get("REMEDIATION_WAIT_SECONDS", "30"))

# Service health probe timeout (in seconds)
# Can be overridden with REMEDIATION_PROBE_TIMEOUT environment variable
PROBE_TIMEOUT = float(os.environ.get("REMEDIATION_PROBE_TIMEOUT", "5.0"))

# Whether to enable debug logging for remediation workflows
# Can be overridden with REMEDIATION_DEBUG environment variable
DEBUG = os.environ.get("REMEDIATION_DEBUG", "").lower() in ("true", "1", "yes")

# N8N webhook URLs for service actions
# Format: service_name -> webhook_url
N8N_WEBHOOKS: Dict[str, str] = {
    "default": os.environ.get(
        "REMEDIATION_N8N_DEFAULT_WEBHOOK", "http://n8n:5678/webhook/restart-service"
    ),
}


def get_webhook_url(service_name: str) -> str:
    """Get the appropriate webhook URL for a service.

    Args:
        service_name: The name of the service to get a webhook for

    Returns:
        The webhook URL to use for the service.
    """
    service_env_var = f"REMEDIATION_N8N_WEBHOOK_{service_name.upper().replace('-', '_')}"

    # Check for service-specific webhook
    if service_env_var in os.environ:
        return os.environ[service_env_var]

    # Fall back to service-specific config
    if service_name in N8N_WEBHOOKS:
        return N8N_WEBHOOKS[service_name]

    # Fall back to default webhook
    return N8N_WEBHOOKS["default"]


def get_settings() -> Dict[str, Any]:
    """Get all remediation settings.

    Returns:
        Dictionary containing all remediation settings.
    """
    return {
        "max_retries": MAX_RETRIES,
        "wait_seconds": DEFAULT_WAIT_SECONDS,
        "probe_timeout": PROBE_TIMEOUT,
        "debug": DEBUG,
        "default_webhook": N8N_WEBHOOKS["default"],
    }
