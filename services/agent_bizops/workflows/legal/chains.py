"""Legal Compliance Chain Components"""

from langchain.chains import LLMChain
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from .models import (
    
,
    ComplianceAuditResult,
    ContractReviewResult,
    DocumentAnalysisResult,
    RegulationCheckResult,
)

# Initialize the LLM
llm = ChatOpenAI(
    model="gpt-4-turbo-preview",
    temperature=0.1,
    openai_api_key="sk-mock-key-for-development-only",
)

# Compliance Audit Chain
audit_parser = PydanticOutputParser(pydantic_object=ComplianceAuditResult)

audit_prompt = PromptTemplate(
    template="""
You are an expert compliance auditor. Perform a comprehensive compliance audit
based on the following information:

Organization: {organization_name}
Audit Scope: {audit_scope}
Compliance Categories: {compliance_categories}
Documents: {documents}

Analyze the organization's compliance status across all specified categories.
Identify any compliance issues, assess risk levels, and provide detailed recommendations.

{format_instructions}

Provide a thorough compliance audit result:.
""",
    input_variables=[
        "organization_name",
        "audit_scope",
        "compliance_categories",
        "documents",
    ],
    partial_variables={"format_instructions": audit_parser.get_format_instructions()},
)

audit_chain = LLMChain(llm=llm, prompt=audit_prompt, output_parser=audit_parser)

# Document Analysis Chain
document_parser = PydanticOutputParser(pydantic_object=DocumentAnalysisResult)

document_prompt = PromptTemplate(
    template="""
You are an expert legal document analyst. Analyze the following document for compliance issues:

Document Type: {document_type}
Document Content: {document_content}
Compliance Frameworks: {compliance_frameworks}
Check for PII: {check_for_pii}

Thoroughly analyze the document for compliance issues, identify any personally
identifiable information (PII), and assess the risk level of any findings.

{format_instructions}

Provide a comprehensive document analysis:.
""",
    input_variables=[
        "document_type",
        "document_content",
        "compliance_frameworks",
        "check_for_pii",
    ],
    partial_variables={"format_instructions": document_parser.get_format_instructions()},
)

document_chain = LLMChain(llm=llm, prompt=document_prompt, output_parser=document_parser)

# Regulation Check Chain
regulation_parser = PydanticOutputParser(pydantic_object=RegulationCheckResult)

regulation_prompt = PromptTemplate(
    template="""
You are an expert regulatory compliance specialist. Check the regulatory requirements for:

Business Activity: {business_activity}
Jurisdictions: {jurisdictions}
Industry Sector: {industry_sector}
Specific Regulations: {specific_regulations}

Identify all applicable regulations, compliance requirements, and potential risk areas.

{format_instructions}

Provide a comprehensive regulation check result:.
""",
    input_variables=[
        "business_activity",
        "jurisdictions",
        "industry_sector",
        "specific_regulations",
    ],
    partial_variables={"format_instructions": regulation_parser.get_format_instructions()},
)

regulation_chain = LLMChain(llm=llm, prompt=regulation_prompt, output_parser=regulation_parser)

# Contract Review Chain
contract_parser = PydanticOutputParser(pydantic_object=ContractReviewResult)

contract_prompt = PromptTemplate(
    template="""
You are an expert contract lawyer. Review the following contract:

Contract Type: {contract_type}
Contract Content: {contract_content}
Parties Involved: {parties_involved}
Jurisdiction: {jurisdiction}
Review Focus Areas: {review_focus}

Analyze the contract for compliance issues, identify key terms, assess risks,
and provide recommendations for improvement.

{format_instructions}

Provide a comprehensive contract review:.
""",
    input_variables=[
        "contract_type",
        "contract_content",
        "parties_involved",
        "jurisdiction",
        "review_focus",
    ],
    partial_variables={"format_instructions": contract_parser.get_format_instructions()},
)

contract_chain = LLMChain(llm=llm, prompt=contract_prompt, output_parser=contract_parser)
