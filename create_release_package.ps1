# TiMEM SDK 发布包打包脚本
# 创建一个完整的发布包，包含所有必要文件

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  TiMEM Python SDK v0.1.1 - 创建发布包" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# 定义变量
$version = "0.1.1"
$packageName = "timem-python-$version-release"
$packageDir = ".\release\$packageName"
$zipFile = ".\release\$packageName.zip"

# 创建临时目录
Write-Host "[1/4] 创建打包目录..." -ForegroundColor Yellow
if (Test-Path ".\release") {
  Remove-Item -Recurse -Force ".\release"
}
New-Item -ItemType Directory -Path $packageDir | Out-Null
Write-Host "✓ 目录创建完成" -ForegroundColor Green
Write-Host ""

# 复制文件
Write-Host "[2/4] 复制文件..." -ForegroundColor Yellow

# 复制 dist 目录下的所有文件
$filesToCopy = @(
  "dist\timem_python-$version-py3-none-any.whl",
  "dist\timem-python-$version.tar.gz",
  "dist\README.txt",
  "dist\install.bat",
  "dist\install.sh",
  "dist\test_connection.py"
)

foreach ($file in $filesToCopy) {
  if (Test-Path $file) {
    Copy-Item $file -Destination $packageDir
    Write-Host "  ✓ 已复制: $file" -ForegroundColor Gray
  }
  else {
    Write-Host "  ⚠ 文件不存在: $file" -ForegroundColor Yellow
  }
}

# 复制文档
if (Test-Path "LOCAL_INSTALL_GUIDE.md") {
  Copy-Item "LOCAL_INSTALL_GUIDE.md" -Destination $packageDir
  Write-Host "  ✓ 已复制: LOCAL_INSTALL_GUIDE.md" -ForegroundColor Gray
}

if (Test-Path "README.md") {
  Copy-Item "README.md" -Destination "$packageDir\README_SDK.md"
  Write-Host "  ✓ 已复制: README.md" -ForegroundColor Gray
}

if (Test-Path "CHANGELOG.md") {
  Copy-Item "CHANGELOG.md" -Destination $packageDir
  Write-Host "  ✓ 已复制: CHANGELOG.md" -ForegroundColor Gray
}

Write-Host "✓ 文件复制完成" -ForegroundColor Green
Write-Host ""

# 创建安装说明
Write-Host "[3/4] 创建安装说明..." -ForegroundColor Yellow
$quickStart = "================================================================
  TiMEM Python SDK v$version - 快速开始
================================================================

包内容
---------
* timem_python-$version-py3-none-any.whl     [SDK Wheel包]
* timem-python-$version.tar.gz               [SDK 源码包]
* test_connection.py                         [连接测试脚本]
* install.bat / install.sh                   [一键安装脚本]
* LOCAL_INSTALL_GUIDE.md                     [详细安装指南]
* README_SDK.md                              [SDK 完整文档]

快速安装（3步）
------------------

Windows 用户:
  1. 双击运行 install.bat
  2. 编辑 test_connection.py（设置API_KEY和BASE_URL）
  3. 运行 python test_connection.py

Linux/Mac 用户:
  1. 运行 chmod +x install.sh && ./install.sh
  2. 编辑 test_connection.py（设置API_KEY和BASE_URL）
  3. 运行 python3 test_connection.py

手动安装
-----------
pip install timem_python-$version-py3-none-any.whl

验证安装
-----------
python -c `"import timem; print(timem.__version__)`"

文档
-------
- 详细安装指南: LOCAL_INSTALL_GUIDE.md
- SDK 完整文档: README_SDK.md
- 更新日志: CHANGELOG.md

使用示例
-----------
from timem import TiMEMClient

client = TiMEMClient(
    api_key=`"your-api-key`",
    base_url=`"http://192.168.1.100:8001`"
)

# 添加记忆
memory = client.add_memory(
    user_id=12345,
    domain=`"aicv`",
    content={`"action`": `"test`"},
    layer_type=`"L1`"
)

client.close()

支持
-------
Email: contact@aigility.com
GitHub: https://github.com/aigility/timem-python

================================================================"

Set-Content -Path "$packageDir\快速开始.txt" -Value $quickStart -Encoding UTF8
Write-Host "✓ 安装说明创建完成" -ForegroundColor Green
Write-Host ""

# 创建压缩包
Write-Host "[4/4] 创建压缩包..." -ForegroundColor Yellow
Compress-Archive -Path "$packageDir\*" -DestinationPath $zipFile -Force
$zipSize = [math]::Round((Get-Item $zipFile).Length / 1KB, 2)
Write-Host "✓ 压缩包创建完成" -ForegroundColor Green
Write-Host ""

# 显示结果
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  ✅ 发布包创建完成！" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📦 发布包信息:" -ForegroundColor Cyan
Write-Host "  - 位置: $zipFile" -ForegroundColor White
Write-Host "  - 大小: $zipSize KB" -ForegroundColor White
Write-Host ""
Write-Host "📁 包含文件:" -ForegroundColor Cyan
Get-ChildItem $packageDir | ForEach-Object {
  $size = [math]::Round($_.Length / 1KB, 2)
  Write-Host "  - $($_.Name) ($size KB)" -ForegroundColor White
}
Write-Host ""
Write-Host "🚀 下一步:" -ForegroundColor Cyan
Write-Host "  1. 将 $zipFile 传输到目标机器" -ForegroundColor White
Write-Host "  2. 解压缩" -ForegroundColor White
Write-Host "  3. 按照 快速开始.txt 中的说明操作" -ForegroundColor White
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan

# 询问是否打开文件夹
$response = Read-Host "是否打开发布包所在文件夹? (Y/N)"
if ($response -eq 'Y' -or $response -eq 'y') {
  explorer ".\release"
}

