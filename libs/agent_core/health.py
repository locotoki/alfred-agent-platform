"""DEPRECATED: This module is maintained for backward compatibility only.

Please use the new health package instead:
    from libs.agent_core.health import create_health_app.
"""

from .health.app_factory import create_health_app

__all__ = ["create_health_app"]