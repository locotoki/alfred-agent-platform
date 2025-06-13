"""Alfred agents module.

This module provides agent implementations including intent routing and orchestration
capabilities.
"""

from alfred.agents.intent_router import Intent, IntentRouter
from alfred.agents.orchestrator import AgentOrchestrator, router

# Create a default orchestrator instance
orchestrator = AgentOrchestrator()
__all__ = ["Intent", "IntentRouter", "router", "AgentOrchestrator", "orchestrator"]
