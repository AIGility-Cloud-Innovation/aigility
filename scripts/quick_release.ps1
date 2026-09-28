param(
    [Parameter(Mandatory=$true)][string]$Version,
    [Parameter(Mandatory=$true)][string]$PyPIToken
)

$ErrorActionPreference = "Stop"

Write-Host "[release] 开始发布 aigility v$Version" -ForegroundColor Cyan

# 1. 更新版本号（pyproject.toml + aigility/__init__.py；当前仓库无 setup.py，包名 aigility 非 aicv）
Write-Host "[release] 更新版本号到 $Version..." -ForegroundColor Yellow
$pyproject = Get-Content -Raw "pyproject.toml"
$pyproject = $pyproject -replace 'version = "[^"]*"', "version = `"$Version`""
$pyproject | Set-Content "pyproject.toml"

$init = Get-Content -Raw "aigility/__init__.py"
$init = $init -replace '__version__ = "[^"]*"', "__version__ = `"$Version`""
$init | Set-Content "aigility/__init__.py"

# 2. 清理旧文件
Write-Host "[release] 清理旧构建文件..." -ForegroundColor Yellow
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "*.egg-info") { Remove-Item -Recurse -Force "*.egg-info" }

# 3. 构建包（python -m build 标准方式）
Write-Host "[release] 构建包..." -ForegroundColor Yellow
python -m pip install --upgrade pip build twine | Out-Null
python -m build

# 4. 发布到PyPI
Write-Host "[release] 发布到PyPI..." -ForegroundColor Yellow
python -m twine upload --username __token__ --password $PyPIToken dist/*

Write-Host "[release] ✅ 发布成功！" -ForegroundColor Green
Write-Host "[release] 查看: https://pypi.org/project/aigility/$Version/" -ForegroundColor Cyan
Write-Host "[release] 建议同步打 tag: git tag v$Version; git push origin v$Version" -ForegroundColor Yellow
