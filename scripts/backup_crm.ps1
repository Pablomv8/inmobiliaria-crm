param(
    [int]$Keep = 30
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot "venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "No se encuentra el entorno virtual en $pythonPath"
}

& $pythonPath (Join-Path $projectRoot "manage.py") backup_crm --keep $Keep
if ($LASTEXITCODE -ne 0) {
    throw "La copia de seguridad no se pudo completar."
}
