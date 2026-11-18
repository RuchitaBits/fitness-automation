$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$python = if (Test-Path ".\.venv\Scripts\python.exe") {
    (Resolve-Path ".\.venv\Scripts\python.exe").Path
} else {
    "python"
}

& $python -m pytest --cov=app --cov-report=xml:coverage.xml --cov-report=term-missing
if ($LASTEXITCODE -ne 0) {
    throw "Pytest or coverage generation failed with exit code $LASTEXITCODE."
}
