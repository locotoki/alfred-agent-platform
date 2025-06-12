"""Standard health module for agent_core package.

This package provides standardized health endpoints for services.
"""

from .app_factory import create_health_app

__all__ = ["create_health_app"]