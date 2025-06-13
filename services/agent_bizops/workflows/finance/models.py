"""Data models for Financial Tax Agent."""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

class TaxJurisdiction(str, Enum):
    """Supported tax jurisdictions.

    This enum defines the tax jurisdictions supported by the Financial Tax Agent.
    Each jurisdiction represents a different tax authority with unique rules.
    """

    US_FEDERAL = "US-FED"
    US_CA = "US-CA"
    US_NY = "US-NY"
    US_TX = "US-TX"
    US_FL = "US-FL"
    UK = "UK"
    EU = "EU"
    CA = "CA"
    AU = "AU"
    SG = "SG"
    JP = "JP"
    IN = "IN"

class EntityType(str, Enum):
    """Entity types for tax calculations.

    This enum represents the different legal entities that can file taxes,
    each with different tax rules, rates, and requirements.
    """

    INDIVIDUAL = "individual"
    CORPORATION = "corporation"
    PARTNERSHIP = "partnership"
    TRUST = "trust"
    NON_PROFIT = "non_profit"

class TaxCalculationRequest(BaseModel):
    """Request model for tax calculation."""

    income: float = Field(..., description="Gross income amount")
    deductions: Dict[str, float] = Field(default_factory=dict, description="Itemized deductions")
    credits: Dict[str, float] = Field(default_factory=dict, description="Tax credits")
    jurisdiction: TaxJurisdiction = Field(..., description="Tax jurisdiction")
    tax_year: int = Field(..., description="Tax year")
    entity_type: EntityType = Field(..., description="Entity type")
    additional_info: Dict[str, Any] = Field(
        default_factory=dict, description="Additional information"
    )

class TaxCalculationResponse(BaseModel):
    """Response model for tax calculation."""

    gross_income: float
    total_deductions: float
    taxable_income: float
    tax_liability: float
    effective_tax_rate: float
    marginal_tax_rate: float
    credits_applied: float
    net_tax_due: float
    breakdown: Dict[str, float]
    calculation_details: List[str]

class FinancialAnalysisRequest(BaseModel):
    """Request model for financial analysis."""

    financial_statements: Dict[str, Dict[str, float]] = Field(
        ..., description="Financial statements data"
    )
    analysis_type: str = Field(..., description="Type of analysis to perform")
    period: str = Field(..., description="Analysis period")
    industry: Optional[str] = Field(None, description="Industry for benchmarking")
    custom_metrics: Optional[List[str]] = Field(None, description="Custom metrics to calculate")

class FinancialAnalysisResponse(BaseModel):
    """Response model for financial analysis."""

    summary: Dict[str, Any]
    key_metrics: Dict[str, float]
    trends: Dict[str, List[float]]
    insights: List[str]
    recommendations: List[str]
    visualizations: Optional[Dict[str, str]] = None
    benchmark_comparison: Optional[Dict[str, Any]] = None

class ComplianceCheckRequest(BaseModel):
    """Request model for tax compliance check."""

    entity_type: EntityType
    transactions: List[Dict[str, Any]]
    jurisdiction: TaxJurisdiction
    tax_year: int
    compliance_areas: List[str] = Field(
        default_factory=list, description="Specific compliance areas to check"
    )

class ComplianceCheckResponse(BaseModel):
    """Response model for compliance check."""

    compliance_status: str = Field(..., description="Overall compliance status")
    issues_found: List[Dict[str, Any]] = Field(
        default_factory=list, description="List of compliance issues"
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Compliance recommendations"
    )
    risk_level: str = Field(..., description="Overall risk level")
    detailed_findings: Dict[str, Any] = Field(
        default_factory=dict, description="Detailed findings by area"
    )

class TaxRateRequest(BaseModel):
    """Request model for tax rate lookup."""

    jurisdiction: TaxJurisdiction
    tax_year: int
    entity_type: EntityType
    income_level: Optional[float] = None
    special_categories: Optional[List[str]] = None

class TaxRateResponse(BaseModel):
    """Response model for tax rate lookup."""

    jurisdiction: TaxJurisdiction
    tax_year: int
    entity_type: EntityType
    tax_brackets: List[Dict[str, Any]]
    standard_deduction: float
    exemptions: Dict[str, float]
    special_rates: Dict[str, float]
    additional_info: Dict[str, Any]
