"""Financial Tax Agent module.

This module has been moved to services.agent_bizops.workflows.finance.
This stub is kept for backward compatibility.
"""

# Re-export from the new location for backward compatibility
try:
    from services.agent_bizops.workflows.finance.agent import FinancialTaxAgent
from services.agent_bizops.workflows.finance.chains import (
    
,
    ComplianceCheckChain,
    FinancialAnalysisChain,
    RateLookupChain,
    TaxCalculationChain,
)
from services.agent_bizops.workflows.finance.models import (
    
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
    __all__ = [
        "FinancialTaxAgent",
        "ComplianceCheckChain",
        "FinancialAnalysisChain",
        "RateLookupChain",
        "TaxCalculationChain",
        "ComplianceCheckRequest",
        "ComplianceCheckResponse",
        "EntityType",
        "FinancialAnalysisRequest",
        "FinancialAnalysisResponse",
        "TaxCalculationRequest",
        "TaxCalculationResponse",
        "TaxJurisdiction",
        "TaxRateRequest",
        "TaxRateResponse",
    ]
except ImportError:
    # If the new location is not available, provide empty module
    pass
