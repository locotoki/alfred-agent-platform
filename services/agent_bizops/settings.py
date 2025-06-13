"""Agent BizOps Settings - Consolidated Configuration."""

import os
from typing import Optional

class BizOpsSettings:
    """Centralized settings for Agent BizOps service."""

    def __init__(self) -> None:
        """Initialize BizOps settings."""
        # Check for legacy environment variables and hard-fail if found
        self._check_legacy_env_vars()

        # API Keys
        self.legal_api_key = os.getenv("BIZOPS_LEGAL_API_KEY", "legal-default-key")
        self.finance_api_key = os.getenv("BIZOPS_FINANCE_API_KEY", "finance-default-key")

        # Database and Redis URLs
        self.database_url = os.getenv("BIZOPS_DATABASE_URL")
        self.redis_url = os.getenv("BIZOPS_REDIS_URL", "redis://redis:6379")

        # RAG configuration
        self.rag_url = os.getenv("BIZOPS_RAG_URL", "http://agent-rag:8501")
        self.rag_legal_api_key = os.getenv("BIZOPS_RAG_LEGAL_KEY", "legal-key")
        self.rag_finance_api_key = os.getenv("BIZOPS_RAG_FINANCE_KEY", "financial-key")

        # Model Router
        self.model_router_url = os.getenv("BIZOPS_MODEL_ROUTER_URL", "http://model-router:8080")

        # OpenAI API Key
        self.openai_api_key = os.getenv("BIZOPS_OPENAI_API_KEY", "sk-mock-key-for-development-only")

    def _check_legacy_env_vars(self) -> None:
        """Check for legacy environment variables and raise error if found."""
        legacy_vars = {
            # Legacy API keys
            "LEGAL_COMPLIANCE_API_KEY": "BIZOPS_LEGAL_API_KEY",
            "AGENT_LEGAL_API_KEY": "BIZOPS_LEGAL_API_KEY",
            "FINANCIAL_TAX_API_KEY": "BIZOPS_FINANCE_API_KEY",
            "AGENT_FINANCIAL_API_KEY": "BIZOPS_FINANCE_API_KEY",
            # Legacy database URLs (agent-specific only)
            "A
RED_DATABASE_URL": "BIZOPS_DATABASE_URL",
            "A
RED_REDIS_URL": "BIZOPS_REDIS_URL",
            # Removed global DATABASE_URL and REDIS_URL to avoid CI conflicts
            # Legacy service URLs
            "A
RED_RAG_URL": "BIZOPS_RAG_URL",
            "A
RED_RAG_LEGAL_KEY": "BIZOPS_RAG_LEGAL_KEY",
            "LEGAL_RAG_KEY": "BIZOPS_RAG_LEGAL_KEY",
            "A
RED_RAG_FINANCE_KEY": "BIZOPS_RAG_FINANCE_KEY",
            "FINANCIAL_RAG_KEY": "BIZOPS_RAG_FINANCE_KEY",
            "A
RED_MODEL_ROUTER_URL": "BIZOPS_MODEL_ROUTER_URL",
            "A
RED_OPENAI_API_KEY": "BIZOPS_OPENAI_API_KEY",
            # Removed global OPENAI_API_KEY check to avoid CI conflicts
        }

        found_legacy = []
        for legacy_var, new_var in legacy_vars.items():
            if os.getenv(legacy_var) is not None:
                found_legacy.append(f"  {legacy_var} → {new_var}")

        if found_legacy:
            error_msg = (
                "Legacy environment variables detected. Agent consolidation is complete.\n"
                "Please update your environment configuration:\n"
                + "\n".join(found_legacy)
                + "\n\nLegacy environment variable support was removed in agent-bizops v2.0.0"
            )
            raise EnvironmentError(error_msg)

# Global settings instance - initialize when first accessed
settings: Optional[BizOpsSettings] = None

def get_settings() -> BizOpsSettings:
    """Get or create the global settings instance."""
    global settings
    if settings is None:
        settings = BizOpsSettings()
    return settings
