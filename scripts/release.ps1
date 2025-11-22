$ErrorActionPreference = "Stop"

param(
  [Parameter(Mandatory=$true)][string]$Version,       # e.g. 0.1.1
  [ValidateSet('test','pypi','none')][string]$Publish = 'none' # where to upload locally
)

function Update-Version-In-File($Path, $Pattern, $Replacement) {
  if (-not (Test-Path $Path)) { throw "File not found: $Path" }
  (Get-Content -Raw $Path) -replace $Pattern, $Replacement | Set-Content -NoNewline $Path
}

Write-Host "[release] Target version: $Version" -ForegroundColor Cyan

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Resolve-Path (Join-Path $root '..')
Set-Location $repo

# 1) Update versions in pyproject.toml and aicv/__init__.py
Write-Host "[release] Updating versions..." -ForegroundColor Cyan
Update-Version-In-File -Path "pyproject.toml" -Pattern 'version\s*=\s*"[^"]+"' -Replacement "version = \"$Version\""
Update-Version-In-File -Path "aicv/__init__.py" -Pattern '__version__\s*=\s*"[^"]+"' -Replacement "__version__ = \"$Version\""

# 2) Commit and tag
git add -A
git commit -m "chore(release): v$Version" | Out-Null
git tag "v$Version" -m "aicv-python v$Version"
git push origin HEAD
git push origin "v$Version"

# 3) Optionally build and upload locally (useful before CI)
if ($Publish -ne 'none') {
  Write-Host "[release] Building artifacts..." -ForegroundColor Cyan
  python -m pip install --upgrade pip | Out-Null
  python -m pip install --upgrade build twine | Out-Null
  if (Test-Path dist) { Remove-Item -Recurse -Force dist }
  if (Test-Path build) { Remove-Item -Recurse -Force build }
  Get-ChildItem -Directory -Filter "*.egg-info" | ForEach-Object { Remove-Item -Recurse -Force $_ }
  python -m build
  twine check dist/*

  if ($Publish -eq 'test') {
    if (-not $env:TWINE_PASSWORD) { throw "Set TWINE_PASSWORD to TestPyPI token" }
    $env:TWINE_USERNAME = "__token__"
    twine upload --repository-url https://test.pypi.org/legacy/ dist/*
  }
  elseif ($Publish -eq 'pypi') {
    if (-not $env:TWINE_PASSWORD) { throw "Set TWINE_PASSWORD to PyPI token" }
    $env:TWINE_USERNAME = "__token__"
    twine upload dist/*
  }
}

Write-Host "[done] Release v$Version pushed. CI will publish on tag." -ForegroundColor Green

