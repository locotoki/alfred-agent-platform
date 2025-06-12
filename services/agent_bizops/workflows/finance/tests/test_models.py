"""Unit tests for Financial Tax Agent models."""

import pytest
from pydantic import ValidationError

from agents.financial_tax.models import (
    
,
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

class TestModels:
    """Test suite for Financial Tax Agent models."""

    def test_tax_calculation_request_valid(self):
        """Test valid tax calculation request."""
        request = TaxCalculationRequest(
            income=100000,
            deductions={"mortgage": 12000},
            credits={"child_credit": 2000},
            jurisdiction=TaxJurisdiction.US_CA,
            tax_year=2024,
            entity_type=EntityType.INDIVIDUAL,
            additional_info={"filing_status": "single"},
        )

        assert request.income == 100000
        assert request.jurisdiction == TaxJurisdiction.US_CA
        assert request.entity_type == EntityType.INDIVIDUAL

    def test_tax_calculation_request_invalid(self):
        """Test invalid tax calculation request."""
        with pytest.raises(ValidationError):
            TaxCalculationRequest(
                income="not_a_number",  # Should be float
                jurisdiction="INVALID",  # Not a valid jurisdiction
                tax_year=2024,
                entity_type=EntityType.INDIVIDUAL,
            )

    def test_financial_analysis_request_valid(self):
        """Test valid financial analysis request."""
        request = FinancialAnalysisRequest(
            financial_statements={
                "income_statement": {"revenue": 1000000, "expenses": 750000},
                "balance_sheet": {"assets": 2000000, "liabilities": 800000},
            },
            analysis_type="profitability",
            period="Q4 2024",
            industry="technology",
            custom_metrics=["gross_margin", "debt_ratio"],
        )

        assert request.analysis_type == "profitability"
        assert request.industry == "technology"
        assert len(request.custom_metrics) == 2

    def test_compliance_check_request_valid(self):
        """Test valid compliance check request."""
        request = ComplianceCheckRequest(
            entity_type=EntityType.CORPORATION,
            transactions=[
                {"type": "sale", "amount": 50000, "date": "2024-01-15"},
                {"type": "expense", "amount": 10000, "date": "2024-01-20"},
            ],
            jurisdiction=TaxJurisdiction.US_NY,
            tax_year=2024,
            compliance_areas=["sales_tax", "income_tax"],
        )

        assert request.entity_type == EntityType.CORPORATION
        assert len(request.transactions) == 2
        assert request.jurisdiction == TaxJurisdiction.US_NY

    def test_tax_rate_request_valid(self):
        """Test valid tax rate request."""
        request = TaxRateRequest(
            jurisdiction=TaxJurisdiction.US_CA,
            tax_year=2024,
            entity_type=EntityType.INDIVIDUAL,
            income_level=100000,
            special_categories=["capital_gains"],
        )

        assert request.jurisdiction == TaxJurisdiction.US_CA
        assert request.income_level == 100000
        assert "capital_gains" in request.special_categories

    def test_tax_calculation_response_valid(self):
        """Test valid tax calculation response."""
        response = TaxCalculationResponse(
            gross_income=100000,
            total_deductions=17000,
            taxable_income=83000,
            tax_liability=20000,
            effective_tax_rate=0.20,
            marginal_tax_rate=0.24,
            credits_applied=2000,
            net_tax_due=18000,
            breakdown={"federal": 15000, "state": 5000},
            calculation_details=["Detail 1", "Detail 2"],
        )

        assert response.gross_income == 100000
        assert response.effective_tax_rate == 0.20
        assert response.net_tax_due == 18000
        assert len(response.calculation_details) == 2

    def test_financial_analysis_response_valid(self):
        """Test valid financial analysis response."""
        response = FinancialAnalysisResponse(
            summary={"overall_health": "strong"},
            key_metrics={"profit_margin": 0.25, "debt_ratio": 0.4},
            trends={"revenue": [100, 120, 140, 160]},
            insights=["Insight 1", "Insight 2"],
            recommendations=["Recommendation 1", "Recommendation 2"],
            visualizations={"chart1": "base64_data"},
            benchmark_comparison={"industry_avg": 0.20},
        )

        assert response.key_metrics["profit_margin"] == 0.25
        assert len(response.insights) == 2
        assert "chart1" in response.visualizations

    def test_compliance_check_response_valid(self):
        """Test valid compliance check response."""
        response = ComplianceCheckResponse(
            compliance_status="partial_compliance",
            issues_found=[
                {"area": "sales_tax", "severity": "high", "description": "Issue 1"},
                {"area": "income_tax", "severity": "low", "description": "Issue 2"},
            ],
            recommendations=["Fix sales tax", "Review income tax"],
            risk_level="medium",
            detailed_findings={
                "sales_tax": "Non-compliant",
                "income_tax": "Mostly compliant",
            },
        )

        assert response.compliance_status == "partial_compliance"
        assert len(response.issues_found) == 2
        assert response.risk_level == "medium"
        assert "sales_tax" in response.detailed_findings

    def test_tax_rate_response_valid(self):
        """Test valid tax rate response."""
        response = TaxRateResponse(
            jurisdiction=TaxJurisdiction.US_CA,
            tax_year=2024,
            entity_type=EntityType.INDIVIDUAL,
            tax_brackets=[
                {"rate": 0.10, "min": 0, "max": 10000},
                {"rate": 0.12, "min": 10001, "max": 40000},
                {"rate": 0.22, "min": 40001, "max": 85000},
            ],
            standard_deduction=13850,
            exemptions={"personal": 4300, "dependent": 3000},
            special_rates={"capital_gains": 0.15, "qualified_dividends": 0.15},
            additional_info={"state_rate": 0.093},
        )

        assert response.jurisdiction == TaxJurisdiction.US_CA
        assert len(response.tax_brackets) == 3
        assert response.standard_deduction == 13850
        assert response.special_rates["capital_gains"] == 0.15

    def test_tax_jurisdiction_enum(self):
        """Test tax jurisdiction enum."""
        assert TaxJurisdiction.US_CA == "US-CA"
        assert TaxJurisdiction.US_NY == "US-NY"
        assert TaxJurisdiction.UK == "UK"

        # Test all values are valid
        valid_jurisdictions = [
            TaxJurisdiction.US_FEDERAL,
            TaxJurisdiction.US_CA,
            TaxJurisdiction.US_NY,
            TaxJurisdiction.US_TX,
            TaxJurisdiction.US_FL,
            TaxJurisdiction.UK,
            TaxJurisdiction.EU,
            TaxJurisdiction.CA,
            TaxJurisdiction.AU,
            TaxJurisdiction.SG,
            TaxJurisdiction.JP,
            TaxJurisdiction.IN,
        ]

        assert len(valid_jurisdictions) == 12

    def test_entity_type_enum(self):
        """Test entity type enum."""
        assert EntityType.INDIVIDUAL == "individual"
        assert EntityType.CORPORATION == "corporation"
        assert EntityType.PARTNERSHIP == "partnership"
        assert EntityType.TRUST == "trust"
        assert EntityType.NON_PROFIT == "non_profit"

        # Test all values are valid
        valid_entities = [
            EntityType.INDIVIDUAL,
            EntityType.CORPORATION,
            EntityType.PARTNERSHIP,
            EntityType.TRUST,
            EntityType.NON_PROFIT,
        ]

        assert len(valid_entities) == 5
