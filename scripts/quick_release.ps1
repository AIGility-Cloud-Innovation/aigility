param(
    [Parameter(Mandatory=$true)][string]$Version,
    [Parameter(Mandatory=$true)][string]$PyPIToken
)

$ErrorActionPreference = "Stop"

Write-Host "[release] 开始发布 aicv-python v$Version" -ForegroundColor Cyan

# 1. 更新版本号
Write-Host "[release] 更新版本号到 $Version..." -ForegroundColor Yellow
$pyproject = Get-Content -Raw "pyproject.toml"
$pyproject = $pyproject -replace 'version = "[^"]*"', "version = `"$Version`""
$pyproject | Set-Content "pyproject.toml"

$init = Get-Content -Raw "aicv/__init__.py"
$init = $init -replace '__version__ = "[^"]*"', "__version__ = `"$Version`""
$init | Set-Content "aicv/__init__.py"

$setup = Get-Content -Raw "setup.py"
$setup = $setup -replace 'version="[^"]*"', "version=`"$Version`""
$setup | Set-Content "setup.py"

# 2. 清理旧文件
Write-Host "[release] 清理旧构建文件..." -ForegroundColor Yellow
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "*.egg-info") { Remove-Item -Recurse -Force "*.egg-info" }

# 3. 构建包
Write-Host "[release] 构建包..." -ForegroundColor Yellow
python setup.py sdist bdist_wheel

# 4. 发布到PyPI
Write-Host "[release] 发布到PyPI..." -ForegroundColor Yellow
python -m twine upload --username __token__ --password $PyPIToken dist/*

Write-Host "[release] ✅ 发布成功！" -ForegroundColor Green
Write-Host "[release] 查看: https://pypi.org/project/aicv-python/$Version/" -ForegroundColor Cyan
