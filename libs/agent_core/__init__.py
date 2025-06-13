"""Stub implementation of agent_core package"""

from .base_agent import BaseAgent
from .health import create_health_app

__all__ = ["create_health_app", "BaseAgent"]