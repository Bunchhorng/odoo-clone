param()
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    docker compose config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Docker Compose configuration is invalid.' }
    docker compose exec -T backend python -m pip check
    if ($LASTEXITCODE -ne 0) { throw 'Python dependency consistency check failed.' }
    docker compose exec -T backend python manage.py check
    if ($LASTEXITCODE -ne 0) { throw 'Django configuration check failed.' }
    docker compose exec -T backend python manage.py makemigrations --check --dry-run
    if ($LASTEXITCODE -ne 0) { throw 'Uncommitted model changes need migrations.' }
    docker compose exec -T backend python manage.py test --noinput
    if ($LASTEXITCODE -ne 0) { throw 'Django tests failed.' }
    docker compose exec -T frontend npm run check
    if ($LASTEXITCODE -ne 0) { throw 'Frontend type checking, linting, tests, or build failed.' }
    Write-Host 'Django checks, migration consistency, backend tests, and frontend checks passed.'
} finally { Pop-Location }
