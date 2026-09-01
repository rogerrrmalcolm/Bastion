$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    $statusOutput = npx supabase status -o json | Out-String
    if ($LASTEXITCODE -ne 0) {
        throw "Supabase is not running. Run 'npx supabase start' first."
    }
    $status = $statusOutput | ConvertFrom-Json
    $environmentPath = Join-Path $projectRoot ".env.services.local"
    $lines = @(
        "REDIS_URL=redis://127.0.0.1:6379/0"
        "DATABASE_URL=$($status.DB_URL)"
        "SUPABASE_URL=$($status.API_URL)"
        "SUPABASE_ANON_KEY=$($status.PUBLISHABLE_KEY)"
        "SUPABASE_SERVICE_ROLE_KEY=$($status.SECRET_KEY)"
        "GEMINI_EMBEDDING_DIMENSIONS=768"
    )
    Set-Content -LiteralPath $environmentPath -Value $lines -Encoding utf8
    Write-Output "Configured $environmentPath"
}
finally {
    Pop-Location
}
