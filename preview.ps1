$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Create the Python environment using the README instructions first.'
}
Write-Host 'Xafapins: http://localhost:8000 — press Ctrl+C to stop.'
& $pythonPath -m http.server 8000 --bind 127.0.0.1 --directory web
