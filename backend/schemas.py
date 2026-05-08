from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    session_id: str | None = Field(
        default=None,
        description="Existing session id. If omitted, a new session is created.",
    )
    company_text: str = Field(
        min_length=20,
        description="Company, market, financial, or deal context to analyze.",
    )


class AnalyzeResponse(BaseModel):
    session_id: str
    market_analysis: str
    financial_analysis: str
    risk_analysis: str
    investment_memo: str


class ChatRequest(BaseModel):
    session_id: str | None = Field(
        default=None,
        description="Existing session id. If omitted, a new session is created.",
    )
    message: str = Field(
        min_length=1,
        description="User prompt for the investment banking assistant.",
    )


class ChatResponse(BaseModel):
    session_id: str
    response: str


class MemoryMessageResponse(BaseModel):
    role: str
    content: str
    created_at: str


class SessionMemoryResponse(BaseModel):
    session_id: str
    messages: list[MemoryMessageResponse]
