$ErrorActionPreference = 'Stop'
$url = 'http://127.0.0.1:8501/'
$alreadyRunning = $false

try {
    $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2
    $alreadyRunning = $response.StatusCode -eq 200
} catch {
    $alreadyRunning = $false
}

if ($alreadyRunning) {
    Write-Host "Dashboard is already running: $url"
    Start-Process $url
    exit 0
}

$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $repo
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw 'Python was not found. Install Python 3 and run: python -m pip install -r requirements.txt'
}

Write-Host "Starting TikTok Shop dashboard: $url"
Write-Host 'Press Ctrl+C to stop the dashboard.'
& $python.Source -m streamlit run ui/app.py --server.address 127.0.0.1 --server.port 8501 --server.headless false --browser.gatherUsageStats false
