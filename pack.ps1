# TiMEM Python SDK v0.1.3 打包脚本
$VERSION = "0.1.3"
$NAME = "timem-python-v$VERSION"
$DIR = "release\v$VERSION"

Write-Host "开始打包 v$VERSION..." -ForegroundColor Cyan

# 清理
if (Test-Path $DIR) { Remove-Item -Recurse -Force $DIR }
if (Test-Path "$NAME.zip") { Remove-Item -Force "$NAME.zip" }

# 创建目录
New-Item -ItemType Directory -Path "$DIR\timem" -Force | Out-Null
New-Item -ItemType Directory -Path "$DIR\examples" -Force | Out-Null
New-Item -ItemType Directory -Path "$DIR\docs" -Force | Out-Null

# 复制文件
Write-Host "复制SDK代码..."
Copy-Item "timem\__init__.py" "$DIR\timem\" -Force
Copy-Item "timem\async_client.py" "$DIR\timem\" -Force
Copy-Item "timem\sync_client.py" "$DIR\timem\" -Force
Copy-Item "timem\connection_pool.py" "$DIR\timem\" -Force
Copy-Item "timem\circuit_breaker.py" "$DIR\timem\" -Force
Copy-Item "timem\monitoring.py" "$DIR\timem\" -Force
Copy-Item "timem\exceptions.py" "$DIR\timem\" -Force

Write-Host "复制示例..."
Copy-Item "examples\basic_usage.py" "$DIR\examples\" -Force
Copy-Item "examples\async_usage.py" "$DIR\examples\" -Force
Copy-Item "test_quick_v013.py" "$DIR\" -Force

Write-Host "复制文档..."
Copy-Item "README.md" "$DIR\docs\" -Force
Copy-Item "ARCHITECTURE.md" "$DIR\docs\" -Force
Copy-Item "CHANGELOG_v0.1.3.md" "$DIR\docs\" -Force
Copy-Item "QUICK_START_v0.1.3.md" "$DIR\docs\" -Force
Copy-Item "SDK_REFACTOR_v0.1.3.md" "$DIR\docs\" -Force

Write-Host "复制配置..."
Copy-Item "setup.py" "$DIR\" -Force
Copy-Item "requirements.txt" "$DIR\" -Force
if (Test-Path "pyproject.toml") { Copy-Item "pyproject.toml" "$DIR\" -Force }

# 构建wheel
Write-Host "构建wheel包..."
try {
    python -m build --wheel --outdir "$DIR\dist" 2>&1 | Out-Null
    $wheel = Get-ChildItem "$DIR\dist\*.whl" | Select-Object -First 1
    if ($wheel) {
        Copy-Item $wheel.FullName "$DIR\" -Force
        Write-Host "  Wheel: $($wheel.Name)" -ForegroundColor Green
    }
} catch {
    Write-Host "  跳过wheel构建" -ForegroundColor Yellow
}

# 打包ZIP
Write-Host "创建ZIP..."
Compress-Archive -Path "$DIR\*" -DestinationPath "$NAME.zip" -CompressionLevel Optimal

$size = [math]::Round((Get-Item "$NAME.zip").Length / 1MB, 2)

Write-Host "`n打包完成!" -ForegroundColor Green
Write-Host "文件: $NAME.zip ($size MB)" -ForegroundColor White
Write-Host "目录: $DIR" -ForegroundColor White

