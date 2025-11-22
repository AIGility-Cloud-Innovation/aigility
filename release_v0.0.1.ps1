# AIGility ADK v0.0.1 发布脚本
# PowerShell 脚本

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "AIGility ADK v0.0.1 发布脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Python 环境
Write-Host "1. 检查 Python 环境..." -ForegroundColor Yellow
$pythonVersion = python --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: 未找到 Python" -ForegroundColor Red
    exit 1
}
Write-Host "   Python 版本: $pythonVersion" -ForegroundColor Green

# 清理旧的构建文件
Write-Host ""
Write-Host "2. 清理旧的构建文件..." -ForegroundColor Yellow
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "*.egg-info") { Remove-Item -Recurse -Force "*.egg-info" }
if (Test-Path "adk.egg-info") { Remove-Item -Recurse -Force "adk.egg-info" }
Write-Host "   ✓ 清理完成" -ForegroundColor Green

# 检查代码格式
Write-Host ""
Write-Host "3. 检查代码格式..." -ForegroundColor Yellow
python -m black --check adk/ 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "   警告: 代码格式检查失败，建议运行 'black adk/'" -ForegroundColor Yellow
} else {
    Write-Host "   ✓ 代码格式检查通过" -ForegroundColor Green
}

# 运行测试（如果有）
Write-Host ""
Write-Host "4. 运行测试..." -ForegroundColor Yellow
if (Test-Path "tests") {
    python -m pytest tests/ -v 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "   警告: 测试失败，但继续构建" -ForegroundColor Yellow
    } else {
        Write-Host "   ✓ 测试通过" -ForegroundColor Green
    }
} else {
    Write-Host "   跳过: 未找到 tests 目录" -ForegroundColor Yellow
}

# 构建包
Write-Host ""
Write-Host "5. 构建包..." -ForegroundColor Yellow
python -m pip install --upgrade build wheel setuptools 2>&1 | Out-Null

# 使用 pyproject.toml 构建
if (Test-Path "adk_pyproject.toml") {
    Copy-Item "adk_pyproject.toml" "pyproject.toml" -Force
    python -m build 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "   错误: 构建失败" -ForegroundColor Red
        exit 1
    }
    Write-Host "   ✓ 构建完成" -ForegroundColor Green
} else {
    # 使用 setup.py 构建
    if (Test-Path "adk_setup.py") {
        python adk_setup.py sdist bdist_wheel 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "   错误: 构建失败" -ForegroundColor Red
            exit 1
        }
        Write-Host "   ✓ 构建完成" -ForegroundColor Green
    } else {
        Write-Host "   错误: 未找到构建配置文件" -ForegroundColor Red
        exit 1
    }
}

# 检查构建产物
Write-Host ""
Write-Host "6. 检查构建产物..." -ForegroundColor Yellow
$distFiles = Get-ChildItem "dist" -ErrorAction SilentlyContinue
if ($distFiles) {
    Write-Host "   构建产物:" -ForegroundColor Green
    foreach ($file in $distFiles) {
        Write-Host "     - $($file.Name) ($([math]::Round($file.Length/1KB, 2)) KB)" -ForegroundColor Cyan
    }
} else {
    Write-Host "   错误: 未找到构建产物" -ForegroundColor Red
    exit 1
}

# 创建发布包
Write-Host ""
Write-Host "7. 创建发布包..." -ForegroundColor Yellow
$releaseDir = "release/v0.0.1"
if (-not (Test-Path "release")) { New-Item -ItemType Directory -Path "release" | Out-Null }
if (Test-Path $releaseDir) { Remove-Item -Recurse -Force $releaseDir }
New-Item -ItemType Directory -Path $releaseDir | Out-Null

# 复制文件
Copy-Item "dist/*" $releaseDir -Force
Copy-Item "adk/README.md" $releaseDir -Force -ErrorAction SilentlyContinue
Copy-Item "CHANGELOG.md" $releaseDir -Force -ErrorAction SilentlyContinue
Copy-Item "DEVELOPMENT.md" $releaseDir -Force -ErrorAction SilentlyContinue
Copy-Item "LICENSE" $releaseDir -Force -ErrorAction SilentlyContinue

# 创建安装说明
$installNote = @"
# AIGility ADK v0.0.1 安装说明

## 从 wheel 文件安装

```bash
pip install aigility_adk-0.0.1-py3-none-any.whl
```

## 从源码安装

```bash
pip install aigility-adk-0.0.1.tar.gz
```

## 开发模式安装

```bash
pip install -e .
```

## 依赖

- Python >= 3.8
- httpx >= 0.24.0
- pydantic >= 2.0.0
- langchain >= 0.1.0
- langgraph >= 0.0.20

## 快速开始

```python
from adk import create_client

client = create_client(
    llm_provider="openai",
    llm_api_key="your-api-key"
)
```

更多信息请参考 README.md
"@
$installNote | Out-File -FilePath "$releaseDir/INSTALL.md" -Encoding UTF8

Write-Host "   ✓ 发布包创建完成: $releaseDir" -ForegroundColor Green

# 显示发布信息
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "发布完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "发布包位置: $releaseDir" -ForegroundColor Yellow
Write-Host ""
Write-Host "下一步:" -ForegroundColor Cyan
Write-Host "1. 检查发布包内容" -ForegroundColor White
Write-Host "2. 测试安装: pip install $releaseDir/aigility_adk-0.0.1-py3-none-any.whl" -ForegroundColor White
Write-Host "3. 上传到 PyPI (可选): twine upload $releaseDir/*" -ForegroundColor White
Write-Host ""
