"""Tests for Financial Tax Agent models."""

import pytest
from pydantic import ValidationError

from services.agent_bizops.workflows.finance.models import (
    ComplianceCheckRequest,
    ComplianceCheckResponse,
    EntityType,
    FinancialAnalysisRequest,
    FinancialAnalysisResponse,
    TaxCalculationRequest,
    TaxCalculationResponse,
    TaxJurisdiction,
    TaxRateRequest,
    TaxRateResponse,
)

# Removed xfail marker for SC-330 async bug


@pytest.mark.skip(reason="FinancialTaxAgent implementation in progress")
class TestTaxCalculationModels:
    """Test cases for Tax Calculation models."""

    def test_tax_calculation_request(self):
        """Test TaxCalculationRequest model."""
        request = TaxCalculationRequest(
            income=150000.0,
            deductions={"standard": 27700.0},
            credits={"child_tax_credit": 4000.0},
            jurisdiction=TaxJurisdiction.US_FEDERAL,
            tax_year=2024,
            entity_type=EntityType.INDIVIDUAL,
            additional_info={"dependents": 2},
        )

        assert request.income == 150000.0
        assert request.jurisdiction == TaxJurisdiction.US_FEDERAL
        assert request.tax_year == 2024
        assert request.deductions.get("standard") == 27700.0
        assert request.credits.get("child_tax_credit") == 4000.0
        assert request.additional_info.get("dependents") == 2

    def test_tax_calculation_response(self):
        """Test TaxCalculationResponse model."""
        response = TaxCalculationResponse(
            gross_income=150000.0,
            total_deductions=27700.0,
            taxable_income=122300.0,
            tax_liability=18000.0,
            effective_tax_rate=12.0,
            marginal_tax_rate=22.0,
            credits_applied=4000.0,
            net_tax_due=14000.0,
            breakdown={"income": 150000.0, "deductions": 27700.0},
            calculation_details=[
                "Standard deduction applied",
                "Child tax credit applied",
            ],
        )

        assert response.gross_income == 150000.0
        assert response.taxable_income == 122300.0
        assert response.net_tax_due == 14000.0
        assert response.effective_tax_rate == 12.0
        assert response.marginal_tax_rate == 22.0


@pytest.mark.skip(reason="FinancialTaxAgent implementation in progress")
class TestFinancialAnalysisModels:
    """Test cases for Financial Analysis models."""

    def test_financial_analysis_request(self):
        """Test FinancialAnalysisRequest model."""
        request = FinancialAnalysisRequest(
            financial_statements={
                "income_statement": {"revenue": 1000000, "expenses": 750000},
                "balance_sheet": {"assets": 500000, "liabilities": 200000},
            },
            analysis_type="profitability",
            period="2024",
            industry="technology",
        )

        assert request.analysis_type == "profitability"
        assert request.period == "2024"
        assert request.industry == "technology"
        assert request.financial_statements["income_statement"]["revenue"] == 1000000

    def test_financial_analysis_response(self):
        """Test FinancialAnalysisResponse model."""
        response = FinancialAnalysisResponse(
            summary={"overall_health": "good"},
            key_metrics={"profit_margin": 25.0, "current_ratio": 2.5},
            trends={"revenue": [100000, 150000, 200000]},
            insights=["Strong profitability metrics"],
            recommendations=["Consider expansion"],
            visualizations=None,
        )

        assert response.key_metrics["profit_margin"] == 25.0
        assert len(response.insights) == 1
        assert len(response.recommendations) == 1


@pytest.mark.skip(reason="FinancialTaxAgent implementation in progress")
class TestComplianceCheckModels:
    """Test cases for Compliance Check models."""

    def test_compliance_check_request(self):
        """Test ComplianceCheckRequest model."""
        request = ComplianceCheckRequest(
            entity_type=EntityType.CORPORATION,
            transactions=[{"type": "sale", "amount": 10000}],
            jurisdiction=TaxJurisdiction.US_CA,
            tax_year=2024,
            compliance_areas=["sales_tax", "employment_tax"],
        )

        assert request.entity_type == EntityType.CORPORATION
        assert request.jurisdiction == TaxJurisdiction.US_CA
        assert len(request.compliance_areas) == 2
        assert request.tax_year == 2024

    def test_compliance_check_response(self):
        """Test ComplianceCheckResponse model."""
        response = ComplianceCheckResponse(
            compliance_status="partially_compliant",
            issues_found=[{"area": "sales_tax", "issue": "Missing nexus registration"}],
            recommendations=["Register for sales tax permit"],
            risk_level="medium",
            detailed_findings={"sales_tax": {"issues": ["nexus"]}},
        )

        assert response.compliance_status == "partially_compliant"
        assert len(response.issues_found) == 1
        assert response.risk_level == "medium"


@pytest.mark.skip(reason="FinancialTaxAgent implementation in progress")
class TestTaxRateModels:
    """Test cases for Tax Rate models."""

    def test_tax_rate_request(self):
        """Test TaxRateRequest model."""
        request = TaxRateRequest(
            jurisdiction=TaxJurisdiction.US_CA,
            tax_year=2024,
            entity_type=EntityType.INDIVIDUAL,
            income_level=150000.0,
        )

        assert request.jurisdiction == TaxJurisdiction.US_CA
        assert request.tax_year == 2024
        assert request.entity_type == EntityType.INDIVIDUAL
        assert request.income_level == 150000.0

    def test_tax_rate_response(self):
        """Test TaxRateResponse model."""
        response = TaxRateResponse(
            jurisdiction=TaxJurisdiction.US_CA,
            tax_year=2024,
            entity_type=EntityType.INDIVIDUAL,
            tax_brackets=[
                {"rate": 1.0, "threshold": 10412, "description": "First bracket"},
                {"rate": 2.0, "threshold": 24684, "description": "Second bracket"},
            ],
            standard_deduction=13850.0,
            exemptions={"personal": 0},
            special_rates={"capital_gains": 20.0},
            additional_info={"notes": ["CA has 9 tax brackets"]},
        )

        assert response.jurisdiction == TaxJurisdiction.US_CA
        assert len(response.tax_brackets) == 2
        assert response.standard_deduction == 13850.0
        assert response.special_rates["capital_gains"] == 20.0


@pytest.mark.skip(reason="FinancialTaxAgent implementation in progress")
class TestModelValidation:
    """Test cases for model validation edge cases."""

    def test_invalid_tax_year(self):
        """Test tax year validation."""
        # Valid request
        request = TaxCalculationRequest(
            income=100000,
            deductions={},
            credits={},
            jurisdiction=TaxJurisdiction.US_FEDERAL,
            tax_year=2024,
            entity_type=EntityType.INDIVIDUAL,
        )
        assert request.tax_year == 2024

        # We can't test invalid years because Pydantic doesn't have validation on tax_year

    def test_negative_income(self):
        """Test negative income is allowed."""
        request = TaxCalculationRequest(
            income=-5000,
            deductions={},
            credits={},
            jurisdiction=TaxJurisdiction.US_FEDERAL,
            tax_year=2024,
            entity_type=EntityType.INDIVIDUAL,
        )
        assert request.income == -5000

    def test_enum_validation(self):
        """Test enum values are validated correctly.

        This test verifies that Pydantic correctly validates enum fields,
        rejecting values that are not valid enum members.
        """
        # Test with invalid jurisdiction by using a string
        with pytest.raises(ValidationError) as exc_info:
            TaxCalculationRequest(
                income=100000,
                deductions={},
                credits={},
                jurisdiction="INVALID_JURISDICTION",
                tax_year=2024,
                entity_type=EntityType.INDIVIDUAL,
            )
        # Verify the error message contains information about valid enum values
        error_str = str(exc_info.value)
        assert "jurisdiction" in error_str
        assert "Input should be" in error_str
        assert "INVALID_JURISDICTION" in error_str

        # Test with invalid entity type
        with pytest.raises(ValidationError) as exc_info:
            TaxCalculationRequest(
                income=100000,
                deductions={},
                credits={},
                jurisdiction=TaxJurisdiction.US_FEDERAL,
                tax_year=2024,
                entity_type="INVALID_ENTITY",
            )
        # Verify the error message contains information about valid enum values
        error_str = str(exc_info.value)
        assert "entity_type" in error_str
        assert "Input should be" in error_str
        assert "INVALID_ENTITY" in error_str

        # Test that using actual enum values works correctly
        valid_request = TaxCalculationRequest(
            income=100000,
            deductions={},
            credits={},
            jurisdiction=TaxJurisdiction.US_FEDERAL,
            tax_year=2024,
            entity_type=EntityType.INDIVIDUAL,
        )
        assert valid_request.jurisdiction == TaxJurisdiction.US_FEDERAL
        assert valid_request.entity_type == EntityType.INDIVIDUAL
