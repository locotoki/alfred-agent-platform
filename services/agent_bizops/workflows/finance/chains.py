"""LangChain implementations for Financial Tax Agent"""

from langchain.chains import LLMChain
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from .models import (
    
,
    ComplianceCheckRequest,
    ComplianceCheckResponse,
    FinancialAnalysisRequest,
    FinancialAnalysisResponse,
    TaxCalculationRequest,
    TaxCalculationResponse,
    TaxRateRequest,
    TaxRateResponse,
)

class TaxCalculationChain:
    """Chain for tax calculation processing"""

    def __init__(self, llm: ChatOpenAI = None):
        """Initialize the tax calculation chain with an optional LLM"""
        self.llm = llm or ChatOpenAI(temperature=0, model="gpt-4")
        self.output_parser = PydanticOutputParser(pydantic_object=TaxCalculationResponse)

        self.prompt = PromptTemplate(
            template="""You are a tax calculation expert. Calculate the tax liability
based on the following information:

Income: {income}
Deductions: {deductions}
Credits: {credits}
Jurisdiction: {jurisdiction}
Tax Year: {tax_year}
Entity Type: {entity_type}
Additional Info: {additional_info}

Provide a detailed tax calculation including:
1. Gross income
2. Total deductions and taxable income
3. Tax liability before credits
4. Credits applied
5. Net tax due
6. Effective and marginal tax rates
7. Detailed breakdown of calculations

{format_instructions}.
""",
            input_variables=[
                "income",
                "deductions",
                "credits",
                "jurisdiction",
                "tax_year",
                "entity_type",
                "additional_info",
            ],
            partial_variables={"format_instructions": self.output_parser.get_format_instructions()},
        )

        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)

    async def calculate(self, request: TaxCalculationRequest) -> TaxCalculationResponse:
        """Process tax calculation request"""
        result = await self.chain.ainvoke(
            {
                "income": request.income,
                "deductions": request.deductions,
                "credits": request.credits,
                "jurisdiction": request.jurisdiction.value,
                "tax_year": request.tax_year,
                "entity_type": request.entity_type.value,
                "additional_info": request.additional_info,
            }
        )

        return self.output_parser.parse(result)

class FinancialAnalysisChain:
    """Chain for financial analysis processing"""

    def __init__(self, llm: ChatOpenAI = None):
        """Initialize the financial analysis chain with an optional LLM"""
        self.llm = llm or ChatOpenAI(temperature=0, model="gpt-4")
        self.output_parser = PydanticOutputParser(pydantic_object=FinancialAnalysisResponse)

        self.prompt = PromptTemplate(
            template="""You are a financial analyst. Analyze the following financial data:

Financial Statements: {financial_statements}
Analysis Type: {analysis_type}
Period: {period}
Industry: {industry}
Custom Metrics: {custom_metrics}

Provide a comprehensive financial analysis including:
1. Summary of financial health
2. Key financial metrics and ratios
3. Trend analysis
4. Strategic insights
5. Recommendations
6. Industry benchmarks if available

{format_instructions}.
""",
            input_variables=[
                "financial_statements",
                "analysis_type",
                "period",
                "industry",
                "custom_metrics",
            ],
            partial_variables={"format_instructions": self.output_parser.get_format_instructions()},
        )

        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)

    async def analyze(self, request: FinancialAnalysisRequest) -> FinancialAnalysisResponse:
        """Process financial analysis request"""
        result = await self.chain.ainvoke(
            {
                "financial_statements": request.financial_statements,
                "analysis_type": request.analysis_type,
                "period": request.period,
                "industry": request.industry,
                "custom_metrics": request.custom_metrics,
            }
        )

        return self.output_parser.parse(result)

class ComplianceCheckChain:
    """Chain for tax compliance checking"""

    def __init__(self, llm: ChatOpenAI = None):
        """Initialize the compliance check chain with an optional LLM"""
        self.llm = llm or ChatOpenAI(temperature=0, model="gpt-4")
        self.output_parser = PydanticOutputParser(pydantic_object=ComplianceCheckResponse)

        self.prompt = PromptTemplate(
            template="""You are a tax compliance expert. Review the following
information for compliance:

Entity Type: {entity_type}
Transactions: {transactions}
Jurisdiction: {jurisdiction}
Tax Year: {tax_year}
Compliance Areas: {compliance_areas}

Perform a comprehensive compliance check and provide:
1. Overall compliance status
2. Specific issues found
3. Risk assessment
4. Detailed findings by compliance area
5. Recommendations for remediation

{format_instructions}.
""",
            input_variables=[
                "entity_type",
                "transactions",
                "jurisdiction",
                "tax_year",
                "compliance_areas",
            ],
            partial_variables={"format_instructions": self.output_parser.get_format_instructions()},
        )

        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)

    async def check_compliance(self, request: ComplianceCheckRequest) -> ComplianceCheckResponse:
        """Process compliance check request"""
        result = await self.chain.ainvoke(
            {
                "entity_type": request.entity_type.value,
                "transactions": request.transactions,
                "jurisdiction": request.jurisdiction.value,
                "tax_year": request.tax_year,
                "compliance_areas": request.compliance_areas,
            }
        )

        return self.output_parser.parse(result)

class RateLookupChain:
    """Chain for tax rate lookup"""

    def __init__(self, llm: ChatOpenAI = None):
        """Initialize the tax rate lookup chain with an optional LLM"""
        self.llm = llm or ChatOpenAI(temperature=0, model="gpt-4")
        self.output_parser = PydanticOutputParser(pydantic_object=TaxRateResponse)

        self.prompt = PromptTemplate(
            template="""You are a tax rate expert. Provide tax rate information for:

Jurisdiction: {jurisdiction}
Tax Year: {tax_year}
Entity Type: {entity_type}
Income Level: {income_level}
Special Categories: {special_categories}

Return comprehensive tax rate information including:
1. Tax brackets and rates
2. Standard deductions
3. Exemptions
4. Special rates for different categories
5. Additional relevant information

{format_instructions}.
""",
            input_variables=[
                "jurisdiction",
                "tax_year",
                "entity_type",
                "income_level",
                "special_categories",
            ],
            partial_variables={"format_instructions": self.output_parser.get_format_instructions()},
        )

        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)

    async def lookup_rates(self, request: TaxRateRequest) -> TaxRateResponse:
        """Process tax rate lookup request"""
        result = await self.chain.ainvoke(
            {
                "jurisdiction": request.jurisdiction.value,
                "tax_year": request.tax_year,
                "entity_type": request.entity_type.value,
                "income_level": request.income_level,
                "special_categories": request.special_categories,
            }
        )

        return self.output_parser.parse(result)
