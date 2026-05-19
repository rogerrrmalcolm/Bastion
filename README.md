# Bastion

Bastion is an AI-powered M&A diligence workspace that turns buyer context, target context, deal questions, and uploaded PDFs into an investment-committee-style report. The system is designed around a multi-agent workflow that mirrors the functional arms of an investment bank: market coverage, financial analysis, risk diligence, and final memo synthesis.

## Technical Overview

- **FastAPI backend** handles the API surface, request validation, CORS, PDF upload routing, and orchestration of the agent workflow.
- **Pydantic schemas** define strict contracts between agents so outputs stay structured, typed, and usable by the frontend.
- **Google Gemini** powers the reasoning layer. It is used for advanced, context-heavy analysis where the model must compare incomplete buyer and target information, separate facts from assumptions, and produce structured JSON responses.
- **Vite + vanilla JavaScript** keeps the frontend lightweight and fast without adding unnecessary framework complexity.
- **Three.js** provides the interactive visual workflow and dashboard experience.
- **Amazon S3** stores uploaded PDFs so diligence materials can be referenced during analysis.

## Multi-Agent Workflow

Bastion imitates how different groups inside a bank contribute to an M&A process:

1. **CFO Orchestrator Agent** creates the execution plan and decides how the work should flow.
2. **Market Agent** acts like sector coverage, analyzing market backdrop, competitive pressure, buyer appetite, and valuation sentiment.
3. **Financial Agent** acts like the financial analysis team, reviewing metrics, quality of earnings, valuation support, working capital, and financing implications.
4. **Risk Agent** acts like diligence, legal, regulatory, cyber, and integration review, translating risks into deal impact and purchase agreement considerations.
5. **Memo Agent** acts like the investment committee synthesis layer, combining all specialist outputs into a recommendation, conditions, open questions, and source limitations.

This structure keeps each analytical task scoped while allowing the final memo to reflect the full deal picture instead of a single generic model response.

## Run locally

```powershell
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

```powershell
cd frontend
npm install
npm run dev
```

## Configuration

Create `Bastion/.env` for backend secrets and deployment settings:

```env
GOOGLE_API_KEY=...
S3_BUCKET=...
AWS_REGION=...
CORS_ORIGINS=http://localhost:5173
```

For deployed frontends, set `VITE_API_BASE_URL` to the backend URL.
