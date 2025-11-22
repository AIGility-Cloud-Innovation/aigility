#!/usr/bin/env pwsh
# TiMEM Python SDK v0.1.3 简化打包脚本

$ErrorActionPreference = "Stop"
$VERSION = "0.1.3"
$RELEASE_NAME = "timem-python-v${VERSION}"
$RELEASE_DIR = "release\v${VERSION}"

Write-Host "`n======================================================================"
Write-Host "  TiMEM Python SDK v${VERSION} - 打包脚本" -ForegroundColor Cyan
Write-Host "======================================================================`n"

# 清理
Write-Host "[1/6] 清理旧文件..." -ForegroundColor Yellow
if (Test-Path $RELEASE_DIR) { Remove-Item -Path $RELEASE_DIR -Recurse -Force }
if (Test-Path "${RELEASE_NAME}.zip") { Remove-Item -Path "${RELEASE_NAME}.zip" -Force }
Write-Host "  OK 清理完成`n" -ForegroundColor Green

# 创建目录
Write-Host "[2/6] 创建目录结构..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path "$RELEASE_DIR\timem" -Force | Out-Null
New-Item -ItemType Directory -Path "$RELEASE_DIR\examples" -Force | Out-Null
New-Item -ItemType Directory -Path "$RELEASE_DIR\docs" -Force | Out-Null
Write-Host "  OK 目录创建完成`n" -ForegroundColor Green

# 复制核心代码
Write-Host "[3/6] 复制SDK代码..." -ForegroundColor Yellow
$coreFiles = @(
    "timem\__init__.py",
    "timem\async_client.py",
    "timem\sync_client.py",
    "timem\connection_pool.py",
    "timem\circuit_breaker.py",
    "timem\monitoring.py",
    "timem\exceptions.py"
)
foreach ($f in $coreFiles) {
    if (Test-Path $f) {
        Copy-Item -Path $f -Destination "$RELEASE_DIR\$f" -Force
        Write-Host "  + $f" -ForegroundColor Gray
    }
}
Write-Host "  OK SDK代码复制完成`n" -ForegroundColor Green

# 复制示例
Write-Host "[4/6] 复制示例和脚本..." -ForegroundColor Yellow
@(
    "examples\basic_usage.py",
    "examples\async_usage.py",
    "test_quick_v013.py"
) | ForEach-Object {
    if (Test-Path $_) {
        $dest = if ($_ -like "examples\*") { "$RELEASE_DIR\$_" } else { "$RELEASE_DIR\$_" }
        Copy-Item -Path $_ -Destination $dest -Force
        Write-Host "  + $_" -ForegroundColor Gray
    }
}
Write-Host "  OK 示例复制完成`n" -ForegroundColor Green

# 复制文档
Write-Host "[5/6] 复制文档..." -ForegroundColor Yellow
@(
    "README.md",
    "ARCHITECTURE.md",
    "CHANGELOG_v0.1.3.md",
    "QUICK_START_v0.1.3.md",
    "SDK_REFACTOR_v0.1.3.md",
    "SIMPLE_USAGE.md",
    "LOCAL_INSTALL_GUIDE.md"
) | ForEach-Object {
    if (Test-Path $_) {
        Copy-Item -Path $_ -Destination "$RELEASE_DIR\docs\" -Force
        Write-Host "  + $_" -ForegroundColor Gray
    }
}
Write-Host "  OK 文档复制完成`n" -ForegroundColor Green

# 复制配置
Write-Host "复制配置文件..." -ForegroundColor Yellow
@("setup.py", "pyproject.toml", "requirements.txt") | ForEach-Object {
    if (Test-Path $_) {
        Copy-Item -Path $_ -Destination "$RELEASE_DIR\" -Force
        Write-Host "  + $_" -ForegroundColor Gray
    }
}

# 尝试构建wheel
Write-Host "`n[6/6] 构建wheel包..." -ForegroundColor Yellow
try {
    python -m build --wheel --outdir "$RELEASE_DIR\dist" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $wheel = Get-ChildItem -Path "$RELEASE_DIR\dist" -Filter "*.whl" | Select-Object -First 1
        if ($wheel) {
            Copy-Item -Path $wheel.FullName -Destination "$RELEASE_DIR\" -Force
            Write-Host "  OK Wheel包构建成功: $($wheel.Name)" -ForegroundColor Green
        }
    } else {
        Write-Host "  SKIP 跳过wheel构建 (运行 'pip install build' 安装构建工具)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  SKIP wheel构建失败，继续打包" -ForegroundColor Yellow
}

# 创建README
$readme = "# TiMEM Python SDK v${VERSION}`n`n## 快速安装`n`n``````bash`npip install timem_python-${VERSION}-py3-none-any.whl`n``````bash`n`n## 验证`n`n``````bash`npython -c `"import timem; print(timem.__version__)`"`n``````bash`n`n## 文档`n`n查看 docs/ 目录中的完整文档。`n"
Set-Content -Path "$RELEASE_DIR\README.txt" -Value $readme -Encoding UTF8

# 打包ZIP
Write-Host "`n正在创建ZIP..." -ForegroundColor Yellow
$zipPath = "${RELEASE_NAME}.zip"
if (Test-Path $zipPath) { Remove-Item -Path $zipPath -Force }
Compress-Archive -Path "$RELEASE_DIR\*" -DestinationPath $zipPath -CompressionLevel Optimal

$zipFile = Get-Item $zipPath
$sizeMB = [math]::Round($zipFile.Length / 1MB, 2)

Write-Host "`n======================================================================"
Write-Host "  打包完成！" -ForegroundColor Green -BackgroundColor Black
Write-Host "======================================================================`n"
Write-Host "文件信息:" -ForegroundColor Cyan
Write-Host "  版本: v${VERSION}" -ForegroundColor White
Write-Host "  文件: ${zipPath}" -ForegroundColor White
Write-Host "  大小: ${sizeMB} MB`n" -ForegroundColor White

Write-Host "包含内容:" -ForegroundColor Cyan
Write-Host "  SDK代码: timem/" -ForegroundColor White
Write-Host "  示例: examples/" -ForegroundColor White
Write-Host "  文档: docs/" -ForegroundColor White
Write-Host "  配置: setup.py, requirements.txt" -ForegroundColor White
if (Test-Path "$RELEASE_DIR\*.whl") {
    Write-Host "  安装包: timem_python-${VERSION}-py3-none-any.whl" -ForegroundColor White
}

Write-Host "`n下一步:" -ForegroundColor Cyan
Write-Host "  1. 解压: Expand-Archive -Path ${zipPath}" -ForegroundColor Gray
Write-Host "  2. 安装: cd $RELEASE_NAME; pip install *.whl" -ForegroundColor Gray
Write-Host "  3. 验证: python test_quick_v013.py`n" -ForegroundColor Gray

