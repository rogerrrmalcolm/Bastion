# Bastion

Bastion is an AI-powered M&A diligence workspace. It compares buyer and target context, routes market, financial, risk, and memo agents, and returns an investment-committee-style report with key risks, evidence gaps, and next steps.

## Stack

- Frontend: Vite, vanilla JavaScript, Three.js
- Backend: FastAPI, Gemini, S3 PDF uploads

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
