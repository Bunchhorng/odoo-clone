param()
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$testProject = 'kerp-check-' + [Guid]::NewGuid().ToString('N').Substring(0, 12)
$localDirectory = [IO.Path]::GetFullPath((Join-Path $projectRoot '.local'))
$testConfiguration = Join-Path $localDirectory ($testProject + '.env')
$composeFile = Join-Path $projectRoot 'compose.yml'
$cleanupAllowed = $false

function New-TestSecret {
    $bytes = New-Object byte[] 32
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($bytes) } finally { $generator.Dispose() }
    return [BitConverter]::ToString($bytes).Replace('-', '').ToLowerInvariant()
}
function Get-AvailablePort {
    $listener = New-Object System.Net.Sockets.TcpListener([Net.IPAddress]::Loopback, 0)
    try { $listener.Start(); return $listener.LocalEndpoint.Port } finally { $listener.Stop() }
}
function Invoke-TestCompose {
    & docker compose -f $composeFile --env-file $testConfiguration -p $testProject @args
    if ($LASTEXITCODE -ne 0) { throw 'A disposable-stack check failed. Your normal ERP project was not targeted.' }
}

Push-Location -LiteralPath $projectRoot
try {
    docker info --format '{{.ServerVersion}}' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Start Docker Desktop before running fresh-stack checks.' }
    $existingContainers = @(docker ps --all --filter "label=com.docker.compose.project=$testProject" --format '{{.ID}}')
    if ($LASTEXITCODE -ne 0) { throw 'Could not inspect the disposable project.' }
    $existingVolumes = @(docker volume ls --filter "label=com.docker.compose.project=$testProject" --format '{{.Name}}')
    if ($LASTEXITCODE -ne 0 -or $existingContainers.Count -or $existingVolumes.Count) { throw 'Unexpected pre-existing test resources; stopped.' }
    $backendPort = Get-AvailablePort
    do { $frontendPort = Get-AvailablePort } while ($frontendPort -eq $backendPort)
    New-Item -ItemType Directory -Path $localDirectory -Force | Out-Null
    $configuration = Get-Content -LiteralPath '.env.example' -Raw -Encoding utf8
    foreach ($placeholder in @('REPLACE_WITH_DJANGO_SECRET_KEY', 'REPLACE_WITH_MYSQL_APP_PASSWORD', 'REPLACE_WITH_MYSQL_ROOT_PASSWORD')) {
        $configuration = $configuration.Replace($placeholder, (New-TestSecret))
    }
    $configuration = $configuration.Replace('COMPOSE_PROJECT_NAME=kerp', "COMPOSE_PROJECT_NAME=$testProject")
    $configuration = $configuration.Replace('BACKEND_PORT=8000', "BACKEND_PORT=$backendPort").Replace('FRONTEND_PORT=5173', "FRONTEND_PORT=$frontendPort")
    $configuration = $configuration.Replace('http://localhost:5173,http://127.0.0.1:5173', "http://localhost:$frontendPort,http://127.0.0.1:$frontendPort")
    [IO.File]::WriteAllText($testConfiguration, $configuration)
    $cleanupAllowed = $true
    Write-Host "Testing disposable Docker project $testProject with new volumes."
    Invoke-TestCompose config --quiet
    Invoke-TestCompose up -d --build --wait --wait-timeout 300
    Invoke-TestCompose exec -T backend python -m pip check
    Invoke-TestCompose exec -T backend python manage.py check
    Invoke-TestCompose exec -T backend python manage.py makemigrations --check --dry-run
    Invoke-TestCompose exec -T backend python manage.py test --noinput
    Invoke-TestCompose exec -T frontend npm run build
    $healthProbe = "fetch('http://127.0.0.1:5173/api/v1/health/').then(async response => { const data = await response.json(); if (!response.ok || data.database !== 'connected') process.exit(1); console.log('Fresh proxy/database health passed.') }).catch(() => process.exit(1))"
    Invoke-TestCompose exec -T frontend node -e $healthProbe
} finally {
    try {
        if ($cleanupAllowed) {
            $expectedVolumes = @("${testProject}_mysql_data", "${testProject}_frontend_node_modules")
            $actualVolumes = @(docker volume ls --filter "label=com.docker.compose.project=$testProject" --format '{{.Name}}')
            if ($LASTEXITCODE -ne 0 -or @($actualVolumes | Where-Object { $_ -notin $expectedVolumes }).Count) {
                throw 'Unexpected disposable volume set; cleanup stopped for inspection.'
            }
            Invoke-TestCompose down --volumes --remove-orphans
        }
        $resolvedConfiguration = [IO.Path]::GetFullPath($testConfiguration)
        $allowedPrefix = $localDirectory + [IO.Path]::DirectorySeparatorChar
        if (-not $resolvedConfiguration.StartsWith($allowedPrefix, [StringComparison]::OrdinalIgnoreCase)) {
            throw 'Unexpected test configuration path; cleanup stopped.'
        }
        if (Test-Path -LiteralPath $resolvedConfiguration) { Remove-Item -LiteralPath $resolvedConfiguration }
    } finally { Pop-Location }
}
Write-Host 'Fresh-container checks passed; disposable containers, test volumes and configuration were removed.'
