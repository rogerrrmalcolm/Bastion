$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    docker compose up -d redis redisinsight
    if ($LASTEXITCODE -ne 0) {
        throw "Redis failed to start."
    }

    npx supabase start
    if ($LASTEXITCODE -ne 0) {
        throw "Supabase failed to start."
    }

    npx supabase migration up --local
    if ($LASTEXITCODE -ne 0) {
        throw "Supabase migrations failed."
    }

    & (Join-Path $PSScriptRoot "configure-local-services.ps1")
    & ".\.venv\Scripts\python.exe" "backend\checkpointing.py"
    & ".\.venv\Scripts\python.exe" "backend\verify_infrastructure.py"
}
finally {
    Pop-Location
}
