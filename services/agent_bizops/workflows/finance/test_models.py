"""Test models for Financial Tax Agent"""

from enum import Enum
from typing import Any, Dict, List, Optional

from langchain.pydantic_v1 import BaseModel, Field

class FilingStatus(str, Enum):
    """Tax filing status"""

    SINGLE = "single"
    MARRIED_JOINT = "married_joint"
    MARRIED_SEPARATE = "married_separate"
    HEAD_OF_HOUSEHOLD = "head_of_household"
    QUALIFYING_WIDOW = "qualifying_widow"

class DeductionType(str, Enum):
    """Types of tax deductions"""

    STANDARD = "standard"
    MORTGAGE_INTEREST = "mortgage_interest"
    PROPERTY_TAX = "property_tax"
    CHARITABLE = "charitable"
    MEDICAL = "medical"
    STATE_LOCAL_TAX = "state_local_tax"
    BUSINESS = "business"
    OTHER = "other"

class CreditType(str, Enum):
    """Types of tax credits"""

    CHILD_TAX_CREDIT = "child_tax_credit"
    EARNED_INCOME = "earned_income"
    EDUCATION = "education"
    RETIREMENT_SAVINGS = "retirement_savings"
    RENEWABLE_ENERGY = "renewable_energy"
    OTHER = "other"

class SeverityLevel(str, Enum):
    """Severity levels for compliance issues"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class TaxDeduction(BaseModel):
    """Tax deduction model"""

    type: DeductionType
    amount: float = Field(..., gt=0)
    description: Optional[str] = None

class TaxCredit(BaseModel):
    """Tax credit model"""

    type: CreditType
    amount: float = Field(..., gt=0)
    description: Optional[str] = None

class TaxCalculationRequest(BaseModel):
    """Request model for tax calculation"""

    gross_income: float = Field(..., ge=0)
    filing_status: FilingStatus
    tax_year: int = Field(..., ge=1900, le=2050)
    deductions: List[Dict[str, Any]] = Field(default_factory=list)
    credits: List[Dict[str, Any]] = Field(default_factory=list)
    additional_income: Dict[str, float] = Field(default_factory=dict)
    dependents: int = Field(default=0, ge=0)

class TaxCalculationResult(BaseModel):
    """Result model for tax calculation"""

    gross_income: float
    total_deductions: float
    taxable_income: float
    tax_liability: float
    total_credits: float
    net_tax_due: float
    effective_tax_rate: float
    marginal_tax_rate: float
    breakdown: Dict[str, Any]

class FinancialAnalysisRequest(BaseModel):
    """Request model for financial analysis"""

    analysis_type: str = Field(..., pattern="^(business_health|tax_planning|investment_analysis)$")
    data: Dict[str, Any]
    time_period: str
    goals: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)

class FinancialAnalysisResult(BaseModel):
    """Result model for financial analysis"""

    analysis_type: str
    metrics: Dict[str, float]
    insights: List[str]
    recommendations: List[str]
    risks: List[str]
    opportunities: List[str]
    projections: Dict[str, Any]
    summary: str

class ComplianceIssue(BaseModel):
    """Model for compliance issues"""

    area: str
    issue: str
    severity: SeverityLevel
    description: Optional[str] = None
    remediation: Optional[str] = None
    deadline: Optional[str] = None

class ComplianceCheckRequest(BaseModel):
    """Request model for compliance check"""

    entity_type: str = Field(..., pattern="^(individual|corporation|partnership|LLC|trust)$")
    jurisdiction: str
    tax_year: int = Field(..., ge=1900, le=2050)
    compliance_areas: List[str] = Field(..., min_items=1)
    review_period: Optional[str] = None
    specific_concerns: List[str] = Field(default_factory=list)

class ComplianceCheckResult(BaseModel):
    """Result model for compliance check"""

    compliance_status: str = Field(..., pattern="^(compliant|partially_compliant|non_compliant)$")
    issues_found: List[Dict[str, Any]] = Field(default_factory=list)
    passing_areas: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    risk_level: str = Field(..., pattern="^(low|medium|high|critical)$")
    next_actions: List[str] = Field(default_factory=list)
    review_date: Optional[str] = None

class TaxBracket(BaseModel):
    """Model for tax brackets"""

    rate: float = Field(..., ge=0, le=100)
    threshold: float = Field(..., ge=0)
    description: Optional[str] = None

class TaxRateRequest(BaseModel):
    """Request model for tax rate lookup"""

    jurisdiction: str
    tax_year: int = Field(..., ge=1900, le=2050)
    entity_type: str = Field(..., pattern="^(individual|corporation|partnership|LLC|trust)$")
    rate_types: List[str] = Field(default_factory=list)
    filing_status: Optional[str] = None

class TaxRateResult(BaseModel):
    """Result model for tax rate lookup"""

    jurisdiction: str
    tax_year: int
    entity_type: str
    tax_brackets: List[Dict[str, Any]]
    special_rates: Dict[str, Any] = Field(default_factory=dict)
    deductions: Dict[str, Any] = Field(default_factory=dict)
    exemptions: Dict[str, Any] = Field(default_factory=dict)
    effective_date: Optional[str] = None
    notes: List[str] = Field(default_factory=list)
