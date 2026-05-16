import os
import re
from pathlib import Path
from uuid import uuid4

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI
from fastapi import File, Form, HTTPException, UploadFile
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
S3_PREFIX = os.getenv("S3_PREFIX", "pdfs").strip("/")

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


def _s3_client():
    region = os.getenv("AWS_REGION")
    if region:
        return boto3.client("s3", region_name=region)
    return boto3.client("s3")


def _safe_pdf_name(filename: str) -> str:
    name = Path(filename or "document.pdf").name
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return name if name.lower().endswith(".pdf") else f"{name or 'document'}.pdf"


@app.post("/documents/upload")
async def upload_pdf_to_s3(
    file: UploadFile = File(...),
    side: str = Form("general"),
) -> dict[str, str]:
    bucket = os.getenv("S3_BUCKET")
    if not bucket:
        raise HTTPException(status_code=500, detail="Set S3_BUCKET in Bastion/.env.")

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported.")

    safe_side = side if side in {"buyer", "target", "general"} else "general"
    key = f"{S3_PREFIX}/{safe_side}/{uuid4()}-{_safe_pdf_name(file.filename)}"

    try:
        _s3_client().upload_fileobj(
            file.file,
            bucket,
            key,
            ExtraArgs={"ContentType": "application/pdf"},
        )
    except (BotoCoreError, ClientError) as error:
        raise HTTPException(status_code=502, detail=f"S3 upload failed: {error}") from error

    return {
        "bucket": bucket,
        "key": key,
        "uri": f"s3://{bucket}/{key}",
        "filename": file.filename,
        "side": safe_side,
    }


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    session = memory_store.get_or_create(request.session_id)
    memory_context = memory_store.get_recent_context(session.session_id)
    memory_store.add_message(session.session_id, "user", request.message)

    prompt = f"""
You are Bastion, an AI-powered investment banking assistant.

Use the session memory to keep continuity with the user. Answer the current
message directly, ask for missing deal/company information when needed, and do
not claim to provide personalized financial advice. Keep the answer concise and
data-driven: lead with numbers, source-backed facts, and exact missing inputs.

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
