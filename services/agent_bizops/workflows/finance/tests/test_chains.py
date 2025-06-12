"""Unit tests for Financial Tax Agent chains."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.financial_tax.chains import (
    
,
    ComplianceCheckChain,
    FinancialAnalysisChain,
    RateLookupChain,
    TaxCalculationChain,
)
from agents.financial_tax.models import (
    
,
    ComplianceCheckRequest,
    EntityType,
    FinancialAnalysisRequest,
    TaxCalculationRequest,
    TaxJurisdiction,
    TaxRateRequest,
)

@pytest.fixture
def mock_llm():
    """Mock LLM for testing chains."""
    with patch("agents.financial_tax.chains.ChatOpenAI") as mock:
        from typing import Any, Optional

from langchain.schema.runnable import Runnable
        class MockLLM(Runnable):
            def invoke(self, input: Any, config: Optional[Any] = None, **kwargs: Any) -> Any:
                return "test response"

            async def ainvoke(self, input: Any, config: Optional[Any] = None, **kwargs: Any) -> Any:
                return "test response"

            def _call(self, *args, **kwargs):
                return "test response"

            def generate(self, *args, **kwargs):
                from langchain.schema import Generation
                return MagicMock(generations=[[Generation(text="test")]])

            def predict(self, *args, **kwargs):
                return "test response"

        llm_instance = MockLLM()
        mock.return_value = llm_instance
        yield llm_instance

@pytest.fixture
def mock_chain():
    """Create a mock chain that can be used for testing."""
    chain = MagicMock()
    chain.ainvoke = AsyncMock()
    return chain

@pytest.fixture
def mock_parser():
    """Create a mock output parser for testing."""
    parser = MagicMock()
    parser.parse = MagicMock()
    return parser

class TestTaxCalculationChain:
    """Test suite for TaxCalculationChain."""

    @pytest.fixture
    def tax_calc_chain(self, mock_chain, mock_parser, mock_llm):
        """Create TaxCalculationChain instance."""
        chain = TaxCalculationChain(llm=mock_llm)
        # Replace the chain and output parser with our mocks
        chain.chain = mock_chain
        chain.output_parser = mock_parser
        return chain

    @pytest.mark.asyncio
    async def test_calculate_success(self, tax_calc_chain):
        """Test successful tax calculation."""
        # Mock the chain result
        mock_result = """
        {
            "gross_income": 100000,
            "total_deductions": 17000,
            "taxable_income": 83000,
            "tax_liability": 20000,
            "effective_tax_rate": 0.20,
            "marginal_tax_rate": 0.24,
            "credits_applied": 2000,
            "net_tax_due": 18000,
            "breakdown": {"federal": 15000, "state": 5000},
            "calculation_details": ["Standard deduction applied", "Tax credit applied"]
        }
        """

        tax_calc_chain.chain.ainvoke.return_value = mock_result

        mock_response = MagicMock(
            gross_income=100000,
            total_deductions=17000,
            taxable_income=83000,
            tax_liability=20000,
            effective_tax_rate=0.20,
            marginal_tax_rate=0.24,
            credits_applied=2000,
            net_tax_due=18000,
            breakdown={"federal": 15000, "state": 5000},
            calculation_details=[
                "Standard deduction applied",
                "Tax credit applied",
            ],
        )
        tax_calc_chain.output_parser.parse.return_value = mock_response

        request = TaxCalculationRequest(
            income=100000,
            deductions={"mortgage": 12000},
            credits={"child_credit": 2000},
            jurisdiction=TaxJurisdiction.US_CA,
            tax_year=2024,
            entity_type=EntityType.INDIVIDUAL,
        )

        result = await tax_calc_chain.calculate(request)

        assert result.gross_income == 100000
        assert result.net_tax_due == 18000
        assert result.effective_tax_rate == 0.20

class TestFinancialAnalysisChain:
    """Test suite for FinancialAnalysisChain."""

    @pytest.fixture
    def analysis_chain(self, mock_chain, mock_parser, mock_llm):
        """Create FinancialAnalysisChain instance."""
        chain = FinancialAnalysisChain(llm=mock_llm)
        # Replace the chain and output parser with our mocks
        chain.chain = mock_chain
        chain.output_parser = mock_parser
        return chain

    @pytest.mark.asyncio
    async def test_analyze_success(self, analysis_chain):
        """Test successful financial analysis."""
        mock_result = """
        {
            "summary": {"overall_health": "strong", "profitability": "above average"},
            "key_metrics": {"gross_margin": 0.25, "debt_to_equity": 0.4},
            "trends": {"revenue_growth": [0.05, 0.07, 0.06, 0.08]},
            "insights": ["Strong revenue growth", "Healthy profit margins"],
            "recommendations": ["Consider expanding operations", "Maintain current debt levels"],
            "visualizations": null,
            "benchmark_comparison": {"industry_avg": 0.20}
        }
        """

        analysis_chain.chain.ainvoke.return_value = mock_result

        mock_response = MagicMock(
            summary={"overall_health": "strong", "profitability": "above average"},
            key_metrics={"gross_margin": 0.25, "debt_to_equity": 0.4},
            trends={"revenue_growth": [0.05, 0.07, 0.06, 0.08]},
            insights=["Strong revenue growth", "Healthy profit margins"],
            recommendations=[
                "Consider expanding operations",
                "Maintain current debt levels",
            ],
            visualizations=None,
            benchmark_comparison={"industry_avg": 0.20},
        )
        analysis_chain.output_parser.parse.return_value = mock_response

        request = FinancialAnalysisRequest(
            financial_statements={
                "income_statement": {"revenue": 1000000, "expenses": 750000},
                "balance_sheet": {"assets": 2000000, "liabilities": 800000},
            },
            analysis_type="profitability",
            period="Q4 2024",
            industry="technology",
        )

        result = await analysis_chain.analyze(request)

        assert result.key_metrics["gross_margin"] == 0.25
        assert len(result.insights) == 2
        assert "Strong revenue growth" in result.insights

class TestComplianceCheckChain:
    """Test suite for ComplianceCheckChain."""

    @pytest.fixture
    def compliance_chain(self, mock_chain, mock_parser, mock_llm):
        """Create ComplianceCheckChain instance."""
        chain = ComplianceCheckChain(llm=mock_llm)
        # Replace the chain and output parser with our mocks
        chain.chain = mock_chain
        chain.output_parser = mock_parser
        return chain

    @pytest.mark.asyncio
    async def test_check_compliance_success(self, compliance_chain):
        """Test successful compliance check."""
        mock_result = """
        {
            "compliance_status": "partial_compliance",
            "issues_found": [
                {"area": "sales_tax", "severity": "high", "description": "Missing tax collection"}
            ],
            "recommendations": ["Register for sales tax collection", "File amended returns"],
            "risk_level": "medium",
            "detailed_findings": {"sales_tax": "Non-compliant", "income_tax": "Compliant"}
        }
        """

        compliance_chain.chain.ainvoke.return_value = mock_result

        mock_response = MagicMock(
            compliance_status="partial_compliance",
            issues_found=[
                {
                    "area": "sales_tax",
                    "severity": "high",
                    "description": "Missing tax collection",
                }
            ],
            recommendations=[
                "Register for sales tax collection",
                "File amended returns",
            ],
            risk_level="medium",
            detailed_findings={
                "sales_tax": "Non-compliant",
                "income_tax": "Compliant",
            },
        )
        compliance_chain.output_parser.parse.return_value = mock_response

        request = ComplianceCheckRequest(
            entity_type=EntityType.CORPORATION,
            transactions=[{"type": "sale", "amount": 50000, "date": "2024-01-15"}],
            jurisdiction=TaxJurisdiction.US_NY,
            tax_year=2024,
            compliance_areas=["sales_tax", "income_tax"],
        )

        result = await compliance_chain.check_compliance(request)

        assert result.compliance_status == "partial_compliance"
        assert result.risk_level == "medium"
        assert len(result.issues_found) == 1

class TestRateLookupChain:
    """Test suite for RateLookupChain."""

    @pytest.fixture
    def rate_lookup_chain(self, mock_chain, mock_parser, mock_llm):
        """Create RateLookupChain instance."""
        chain = RateLookupChain(llm=mock_llm)
        # Replace the chain and output parser with our mocks
        chain.chain = mock_chain
        chain.output_parser = mock_parser
        return chain

    @pytest.mark.asyncio
    async def test_lookup_rates_success(self, rate_lookup_chain):
        """Test successful tax rate lookup."""
        mock_result = """
        {
            "jurisdiction": "US-CA",
            "tax_year": 2024,
            "entity_type": "individual",
            "tax_brackets": [
                {"rate": 0.10, "min": 0, "max": 10000},
                {"rate": 0.12, "min": 10001, "max": 40000}
            ],
            "standard_deduction": 13850,
            "exemptions": {"personal": 4300},
            "special_rates": {"capital_gains": 0.15},
            "additional_info": {"state_rate": 0.093}
        }
        """

        rate_lookup_chain.chain.ainvoke.return_value = mock_result

        mock_response = MagicMock(
            jurisdiction="US-CA",
            tax_year=2024,
            entity_type="individual",
            tax_brackets=[
                {"rate": 0.10, "min": 0, "max": 10000},
                {"rate": 0.12, "min": 10001, "max": 40000},
            ],
            standard_deduction=13850,
            exemptions={"personal": 4300},
            special_rates={"capital_gains": 0.15},
            additional_info={"state_rate": 0.093},
        )
        rate_lookup_chain.output_parser.parse.return_value = mock_response

        request = TaxRateRequest(
            jurisdiction=TaxJurisdiction.US_CA,
            tax_year=2024,
            entity_type=EntityType.INDIVIDUAL,
            income_level=100000,
        )

        result = await rate_lookup_chain.lookup_rates(request)

        assert result.jurisdiction == "US-CA"
        assert result.standard_deduction == 13850
        assert len(result.tax_brackets) == 2
        assert result.special_rates["capital_gains"] == 0.15
