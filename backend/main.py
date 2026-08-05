import logging
import os
import re
from pathlib import Path
from uuid import uuid4

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
from fastapi import FastAPI
from fastapi import File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from agents.workflow import (
    get_diligence_graph_manifest,
    run_investment_banking_workflow,
)
from gemini_client import call_gemini
from memory import memory_store
from schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    ChatRequest,
    ChatResponse,
    MemoryMessageResponse,
    SessionMemoryResponse,
    WorkflowGraphManifest,
)


app = FastAPI(title="Bastion AI Investment Banking Backend")
logger = logging.getLogger("bastion")
S3_PREFIX = os.getenv("S3_PREFIX", "pdfs").strip("/")
DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def _env_status(name: str) -> str:
    return "set" if os.getenv(name) else "missing"


def _aws_credentials_error_detail() -> str:
    return (
        "S3 credentials not found by the backend process. "
        "For local runs, configure AWS in the same Windows user account and restart the backend. "
        "For Google Cloud, set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY on the deployed backend service, "
        "then create a new revision/redeploy. "
        "Runtime env status: "
        f"AWS_ACCESS_KEY_ID={_env_status('AWS_ACCESS_KEY_ID')}, "
        f"AWS_SECRET_ACCESS_KEY={_env_status('AWS_SECRET_ACCESS_KEY')}, "
        f"AWS_SESSION_TOKEN={_env_status('AWS_SESSION_TOKEN')}, "
        f"AWS_PROFILE={_env_status('AWS_PROFILE')}, "
        f"AWS_REGION={_env_status('AWS_REGION')}, "
        f"AWS_DEFAULT_REGION={_env_status('AWS_DEFAULT_REGION')}."
    )


def _cors_origins() -> list[str]:
    configured_origins = os.getenv("CORS_ORIGINS") or os.getenv("FRONTEND_URL")
    if not configured_origins:
        return DEFAULT_CORS_ORIGINS
    return [
        origin.strip().rstrip("/")
        for origin in configured_origins.split(",")
        if origin.strip()
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "bastion-backend"}


@app.get("/workflow/graph", response_model=WorkflowGraphManifest)
def get_workflow_graph() -> WorkflowGraphManifest:
    return get_diligence_graph_manifest()


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
    except NoCredentialsError as error:
        raise HTTPException(
            status_code=401,
            detail=_aws_credentials_error_detail(),
        ) from error
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
    try:
        return run_investment_banking_workflow(request)
    except Exception as error:
        logger.exception("Analyze workflow failed")
        detail = str(error).replace("\n", " ")[:500] or type(error).__name__
        raise HTTPException(
            status_code=500,
            detail=f"Workflow failed in backend: {type(error).__name__}: {detail}",
        ) from error


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
