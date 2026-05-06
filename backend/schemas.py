from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    company_text: str = Field(
        min_length=20,
        description="Company, market, financial, or deal context to analyze.",
    )


class AnalyzeResponse(BaseModel):
    market_analysis: str
    financial_analysis: str
    risk_analysis: str
    investment_memo: str
