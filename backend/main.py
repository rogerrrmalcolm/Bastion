from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.agents.workflow import run_investment_banking_workflow
from backend.schemas import AnalyzeRequest, AnalyzeResponse


app = FastAPI(title="Bastion API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health_check():
    return {"status": "Bastion backend running"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze_company(request: AnalyzeRequest):
    return run_investment_banking_workflow(request)
