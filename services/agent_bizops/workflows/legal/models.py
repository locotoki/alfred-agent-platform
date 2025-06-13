"""Legal Compliance Agent Models"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

# Use LangChain's Pydantic v1 for compatibility
from langchain.pydantic_v1 import BaseModel, Field

class ComplianceCategory(str, Enum):
    GDPR = "gdpr"
    CCPA = "ccpa"
    HIPAA = "hipaa"
    SOX = "sox"
    PCI_DSS = "pci_dss"
    ISO_27001 = "iso_27001"
    GENERAL = "general"

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class DocumentType(str, Enum):
    CONTRACT = "contract"
    POLICY = "policy"
    AGREEMENT = "agreement"
    REGULATION = "regulation"
    REPORT = "report"
    OTHER = "other"

# Request Models
class ComplianceAuditRequest(BaseModel):
    """Request model for compliance audit"""

    organization_name: str
    audit_scope: List[str]
    compliance_categories: List[ComplianceCategory]
    documents: Optional[List[Dict[str, Any]]] = None
    include_recommendations: bool = True

class DocumentAnalysisRequest(BaseModel):
    """Request model for document analysis"""

    document_type: DocumentType
    document_content: str
    document_metadata: Optional[Dict[str, Any]] = None
    compliance_frameworks: List[ComplianceCategory]
    check_for_pii: bool = True

class RegulationCheckRequest(BaseModel):
    """Request model for regulation checks"""

    business_activity: str
    jurisdictions: List[str]
    industry_sector: str
    specific_regulations: Optional[List[str]] = None

class ContractReviewRequest(BaseModel):
    """Request model for contract review"""

    contract_type: str
    contract_content: str
    parties_involved: List[str]
    jurisdiction: str
    review_focus: List[str] = Field(
        default=["compliance", "risks", "obligations"],
        description="Areas to focus on during review",
    )

# Result Models
class ComplianceIssue(BaseModel):
    """Compliance issue model"""

    issue_id: str
    category: ComplianceCategory
    description: str
    risk_level: RiskLevel
    affected_sections: List[str]
    recommendations: List[str]

class ComplianceAuditResult(BaseModel):
    """Result model for compliance audit"""

    audit_id: str
    organization_name: str
    audit_date: datetime
    overall_compliance_score: float
    issues_found: List[ComplianceIssue]
    recommendations: List[str]
    executive_summary: str

class DocumentAnalysisResult(BaseModel):
    """Result model for document analysis"""

    document_id: str
    document_type: DocumentType
    analysis_date: datetime
    compliance_issues: List[ComplianceIssue]
    pii_detected: bool
    pii_locations: Optional[List[Dict[str, Any]]] = None
    risk_assessment: Dict[str, Any]
    summary: str

class RegulationCheckResult(BaseModel):
    """Result model for regulation checks"""

    check_id: str
    business_activity: str
    applicable_regulations: List[Dict[str, Any]]
    compliance_requirements: List[Dict[str, Any]]
    risk_areas: List[Dict[str, Any]]
    recommendations: List[str]

class ContractReviewResult(BaseModel):
    """Result model for contract review"""

    review_id: str
    contract_type: str
    review_date: datetime
    parties: List[str]
    key_terms: List[Dict[str, Any]]
    compliance_issues: List[ComplianceIssue]
    risk_assessment: Dict[str, Any]
    recommendations: List[str]
    executive_summary: str
