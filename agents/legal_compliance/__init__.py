"""Legal Compliance Agent module.

This module has been moved to services.agent_bizops.workflows.legal.
This stub is kept for backward compatibility.
"""

# Re-export from the new location for backward compatibility
try:
    from services.agent_bizops.workflows.legal.agent import LegalComplianceAgent
from services.agent_bizops.workflows.legal.chains import (
    
,
    ComplianceCheckChain,
    LegalAnalysisChain,
    RegulationLookupChain,
)
from services.agent_bizops.workflows.legal.models import (
    
,
    ComplianceCheckRequest,
    ComplianceCheckResponse,
    LegalAnalysisRequest,
    LegalAnalysisResponse,
    RegulationLookupRequest,
    RegulationLookupResponse,
)
    __all__ = [
        "LegalComplianceAgent",
        "ComplianceCheckChain",
        "LegalAnalysisChain",
        "RegulationLookupChain",
        "ComplianceCheckRequest",
        "ComplianceCheckResponse",
        "LegalAnalysisRequest",
        "LegalAnalysisResponse",
        "RegulationLookupRequest",
        "RegulationLookupResponse",
    ]
except ImportError:
    # If the new location is not available, provide empty module
    pass
