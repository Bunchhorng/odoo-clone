param()
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot

function New-LocalSecret {
    $bytes = New-Object byte[] 32
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($bytes) } finally { $generator.Dispose() }
    return [BitConverter]::ToString($bytes).Replace('-', '').ToLowerInvariant()
}

Push-Location -LiteralPath $projectRoot
try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw 'Install and start Docker Desktop, then run this script again.'
    }
    docker info --format '{{.ServerVersion}}' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Start Docker Desktop and wait until its engine is ready.' }
    if (-not (Test-Path -LiteralPath '.env')) {
        $configuration = Get-Content -LiteralPath '.env.example' -Raw
        foreach ($placeholder in @('REPLACE_WITH_DJANGO_SECRET_KEY', 'REPLACE_WITH_MYSQL_APP_PASSWORD', 'REPLACE_WITH_MYSQL_ROOT_PASSWORD')) {
            $configuration = $configuration.Replace($placeholder, (New-LocalSecret))
        }
        [IO.File]::WriteAllText((Join-Path $projectRoot '.env'), $configuration)
        Write-Host 'Created .env with independent local secrets. No account password was created.'
    }
    if ((Get-Content -LiteralPath '.env' -Raw).Contains('REPLACE_WITH_')) {
        throw 'Your existing .env still contains placeholders. Replace them as explained in SETUP.md. Existing secrets were preserved.'
    }
    docker compose config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Docker Compose configuration is invalid. Check .env and SETUP.md.' }
    docker compose up -d --build --wait --wait-timeout 300
    if ($LASTEXITCODE -ne 0) { throw 'Services did not become healthy. Run docker compose logs --tail=80 and read SETUP.md.' }
    docker compose ps
    $frontendPort = '5175'
    foreach ($line in (Get-Content -LiteralPath '.env')) {
        if ($line -match '^FRONTEND_PORT=(\d+)\s*$') { $frontendPort = $Matches[1] }
    }
    Write-Host "Ready: http://localhost:$frontendPort/login"
    Write-Host 'First run: docker compose exec backend python manage.py createsuperuser'
    Write-Host 'Then follow docs/USER-GUIDE.md to create a company and add teammates.'
    Write-Host 'Password recovery mail is processed by the mailer service. See docs/FOUNDATION.md.'
} finally { Pop-Location }
