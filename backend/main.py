from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.agents.workflow import (
    ParallelAgent,
    SequentialAgent,
    run_investment_banking_workflow,
)
from backend.gemini_client import call_gemini
from backend.memory import memory_store
from backend.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    ChatRequest,
    ChatResponse,
    MemoryMessageResponse,
    SessionMemoryResponse,
)


app = FastAPI(title="Bastion AI Investment Banking Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "bastion-backend"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    session = memory_store.get_or_create(request.session_id)
    memory_context = memory_store.get_recent_context(session.session_id)
    memory_store.add_message(session.session_id, "user", request.message)

    prompt = f"""
You are Bastion, an AI-powered investment banking assistant.

Use the session memory to keep continuity with the user. Answer the current
message directly, ask for missing deal/company information when needed, and do
not claim to provide personalized financial advice.

Session memory:
{memory_context}

Current user message:
{request.message}
"""

    response = call_gemini(prompt)
    memory_store.add_message(session.session_id, "assistant", response)

    return ChatResponse(session_id=session.session_id, response=response)


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    return run_investment_banking_workflow(request)


@app.get("/sessions/{session_id}/memory", response_model=SessionMemoryResponse)
def get_session_memory(session_id: str) -> SessionMemoryResponse:
    session = memory_store.get_or_create(session_id)
    messages = memory_store.list_messages(session.session_id)

    return SessionMemoryResponse(
        session_id=session.session_id,
        messages=[
            MemoryMessageResponse(
                role=message.role,
                content=message.content,
                created_at=message.created_at.isoformat(),
            )
            for message in messages
        ],
    )
