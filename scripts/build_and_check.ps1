$ErrorActionPreference = "Stop"

Write-Host "[build] Installing tools..." -ForegroundColor Cyan
python -m pip install --upgrade pip | Out-Null
python -m pip install --upgrade build twine | Out-Null

Write-Host "[build] Cleaning dist/build/egg-info..." -ForegroundColor Cyan
if (Test-Path dist) { Remove-Item -Recurse -Force dist }
if (Test-Path build) { Remove-Item -Recurse -Force build }
Get-ChildItem -Directory -Filter "*.egg-info" | ForEach-Object { Remove-Item -Recurse -Force $_ }

Write-Host "[build] Building package..." -ForegroundColor Cyan
python -m build

Write-Host "[check] Running twine check..." -ForegroundColor Cyan
twine check dist/*

Write-Host "[done] Artifacts ready in ./dist" -ForegroundColor Green

