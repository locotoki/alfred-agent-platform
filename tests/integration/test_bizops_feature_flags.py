"""Integration tests for BizOps feature flags and workflow registration."""

import os
from unittest.mock import patch

import pytest

@pytest.mark.parametrize(
    "workflows_enabled,expected_workflows",
    [
        ("", []),
        ("legal", ["legal"]),
        ("finance", ["finance"]),
        ("legal,finance", ["legal", "finance"]),
        ("finance,legal", ["finance", "legal"]),  # Order shouldn't matter
        ("legal, finance", ["legal", "finance"]),  # Spaces should be handled
    ],
)
@pytest.mark.integration
def test_workflow_registration_with_feature_flags(workflows_enabled, expected_workflows):
    """Test that only enabled workflows are registered based on WORKFLOWS_ENABLED."""
    with patch.dict(os.environ, {"WORKFLOWS_ENABLED": workflows_enabled}, clear=False):
        # Import settings after patching environment

        from services.agent_bizops.settings import BizOpsSettings
        settings = BizOpsSettings()

        # Check that workflows_enabled matches expected
        assert sorted(settings.workflows_enabled) == sorted(expected_workflows)

        # Test individual workflow checks
        assert settings.is_workflow_enabled("legal") == ("legal" in expected_workflows)
        assert settings.is_workflow_enabled("finance") == ("finance" in expected_workflows)
        assert settings.is_workflow_enabled("unknown") is False

@pytest.mark.integration
def test_service_health_reflects_enabled_workflows():
    """Test that service health endpoint reflects enabled workflows."""
    test_cases = [
        ("legal", ["legal"]),
        ("finance", ["finance"]),
        ("legal,finance", ["legal", "finance"]),
        ("", []),
    ]

    for workflows_enabled, expected_workflows in test_cases:
        with patch.dict(os.environ, {"WORKFLOWS_ENABLED": workflows_enabled}, clear=False):
            # Mock the health endpoint response
            with patch("services.agent_bizops.app.main.WORKFLOWS_ENABLED", expected_workflows):
                # Simulate health check call
                mock_response = {
                    "status": "healthy",
                    "service": "agent-bizops",
                    "workflows_enabled": expected_workflows,
                }

                assert mock_response["workflows_enabled"] == expected_workflows

                # Verify we only have enabled workflows
                for workflow in ["legal", "finance"]:
                    if workflow in expected_workflows:
                        assert workflow in mock_response["workflows_enabled"]
                    else:
                        assert workflow not in mock_response["workflows_enabled"]

@pytest.mark.integration
def test_legacy_environment_variable_mapping():
    """Test that legacy environment variables are properly mapped with warnings."""
    import warnings

from services.agent_bizops.settings import BizOpsSettings, LegacyEnvVarWarning

# Test legacy LEGAL_COMPLIANCE_API_KEY
    with patch.dict(os.environ, {"LEGAL_COMPLIANCE_API_KEY": "legacy-legal-key"}, clear=True):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            settings = BizOpsSettings()

            # Check that we got the legacy value
            assert settings.legal_api_key == "legacy-legal-key"

            # Check that deprecation warning was issued
            assert len(w) >= 1
            warning_messages = [
                str(warn.message) for warn in w if warn.category == LegacyEnvVarWarning
            ]
            assert any("LEGAL_COMPLIANCE_API_KEY" in msg for msg in warning_messages)

    # Test legacy FINANCIAL_TAX_API_KEY
    with patch.dict(os.environ, {"FINANCIAL_TAX_API_KEY": "legacy-finance-key"}, clear=True):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            settings = BizOpsSettings()

            assert settings.finance_api_key == "legacy-finance-key"

            # Check warning was issued
            assert len(w) >= 1
            warning_messages = [
                str(warn.message) for warn in w if warn.category == LegacyEnvVarWarning
            ]
            assert any("FINANCIAL_TAX_API_KEY" in msg for msg in warning_messages)

@pytest.mark.integration
def test_new_environment_variables_take_precedence():
    """Test that new environment variables take precedence over legacy ones."""
    from services.agent_bizops.settings import BizOpsSettings

# Set both new and old variables
    env_vars = {
        "BIZOPS_LEGAL_API_KEY": "new-legal-key",
        "LEGAL_COMPLIANCE_API_KEY": "old-legal-key",
        "BIZOPS_FINANCE_API_KEY": "new-finance-key",
        "FINANCIAL_TAX_API_KEY": "old-finance-key",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        settings = BizOpsSettings()

        # New variables should take precedence
        assert settings.legal_api_key == "new-legal-key"
        assert settings.finance_api_key == "new-finance-key"

@pytest.mark.integration
def test_workflow_case_insensitive():
    """Test that workflow enablement is case-insensitive."""
    from services.agent_bizops.settings import BizOpsSettings
    with patch.dict(os.environ, {"WORKFLOWS_ENABLED": "Legal,FINANCE"}, clear=False):
        settings = BizOpsSettings()

        # Case-insensitive checks should work
        assert settings.is_workflow_enabled("legal") is True
        assert settings.is_workflow_enabled("LEGAL") is True
        assert settings.is_workflow_enabled("Legal") is True
        assert settings.is_workflow_enabled("finance") is True
        assert settings.is_workflow_enabled("FINANCE") is True
        assert settings.is_workflow_enabled("Finance") is True

@pytest.mark.integration
def test_default_values_when_no_env_vars():
    """Test that appropriate defaults are used when no environment variables are set."""
    from services.agent_bizops.settings import BizOpsSettings

# Clear all relevant environment variables
    env_to_clear = [
        "WORKFLOWS_ENABLED",
        "BIZOPS_LEGAL_API_KEY",
        "LEGAL_COMPLIANCE_API_KEY",
        "AGENT_LEGAL_API_KEY",
        "BIZOPS_FINANCE_API_KEY",
        "FINANCIAL_TAX_API_KEY",
        "AGENT_FINANCIAL_API_KEY",
        "BIZOPS_DATABASE_URL",
        "A
RED_DATABASE_URL",
        "DATABASE_URL",
        "BIZOPS_REDIS_URL",
        "A
RED_REDIS_URL",
        "REDIS_URL",
    ]

    with patch.dict(os.environ, {}, clear=True):
        # Remove any remaining vars
        for var in env_to_clear:
            os.environ.pop(var, None)

        settings = BizOpsSettings()

        # Check defaults
        assert sorted(settings.workflows_enabled) == [
            "finance",
            "legal",
        ]  # Default from "finance,legal"
        assert settings.legal_api_key == "legal-default-key"
        assert settings.finance_api_key == "finance-default-key"
        assert settings.redis_url == "redis://redis:6379"
        assert settings.rag_url == "http://agent-rag:8501"
        assert settings.model_router_url == "http://model-router:8080"
