"""End-to-end test for contract review functionality in agent-bizops"""

import pytest
from playwright.sync_api import Page, expect

@pytest.mark.e2e
def test_contract_review_workflow(page: Page):
    """Test the contract review workflow in agent-bizops"""
    # Navigate to agent-bizops service
    page.goto("http://localhost:8080")

    # Verify service is running
    expect(page.locator("body")).to_contain_text("Agent BizOps Service")

    # Check health endpoint
    page.goto("http://localhost:8080/health")
    response_text = page.locator("body").text_content()
    assert "healthy" in response_text
    assert "legal" in response_text

@pytest.mark.e2e
def test_finance_workflow_available(page: Page):
    """Test that finance workflow is available in agent-bizops"""
    # Navigate to agent-bizops service
    page.goto("http://localhost:8080/health")

    # Verify finance workflow is enabled
    response_text = page.locator("body").text_content()
    assert "finance" in response_text
