#!/usr/bin/env pwsh
# TiMEM Python SDK v0.1.3 打包脚本
# 用于创建完整的发布包

$ErrorActionPreference = "Stop"

# 配置
$VERSION = "0.1.3"
$PACKAGE_NAME = "timem-python"
$RELEASE_NAME = "${PACKAGE_NAME}-v${VERSION}"
$RELEASE_DIR = "release\v${VERSION}"
$DIST_DIR = "dist"

Write-Host ""
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "  TiMEM Python SDK v${VERSION} - 打包脚本" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""

# 步骤1: 清理旧的发布文件
Write-Host "[1/7] 清理旧的发布文件..." -ForegroundColor Yellow
if (Test-Path $RELEASE_DIR) {
  Remove-Item -Path $RELEASE_DIR -Recurse -Force
  Write-Host "  已删除旧的发布目录" -ForegroundColor Gray
}
if (Test-Path "${RELEASE_NAME}.zip") {
  Remove-Item -Path "${RELEASE_NAME}.zip" -Force
  Write-Host "  已删除旧的zip文件" -ForegroundColor Gray
}
Write-Host "  ✓ 清理完成" -ForegroundColor Green

# 步骤2: 创建发布目录结构
Write-Host ""
Write-Host "[2/7] 创建发布目录结构..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path $RELEASE_DIR -Force | Out-Null
New-Item -ItemType Directory -Path "$RELEASE_DIR\timem" -Force | Out-Null
New-Item -ItemType Directory -Path "$RELEASE_DIR\examples" -Force | Out-Null
New-Item -ItemType Directory -Path "$RELEASE_DIR\docs" -Force | Out-Null
New-Item -ItemType Directory -Path "$RELEASE_DIR\tests" -Force | Out-Null
Write-Host "  ✓ 目录结构创建完成" -ForegroundColor Green

# 步骤3: 复制核心代码
Write-Host ""
Write-Host "[3/7] 复制核心代码..." -ForegroundColor Yellow

# 复制 timem 包
$timemFiles = @(
  "timem\__init__.py",
  "timem\async_client.py",
  "timem\sync_client.py",
  "timem\connection_pool.py",
  "timem\circuit_breaker.py",
  "timem\monitoring.py",
  "timem\exceptions.py"
)

foreach ($file in $timemFiles) {
  if (Test-Path $file) {
    Copy-Item -Path $file -Destination "$RELEASE_DIR\$file" -Force
    Write-Host "  ✓ $file" -ForegroundColor Gray
  }
  else {
    Write-Host "  ⚠ 未找到: $file" -ForegroundColor Yellow
  }
}

Write-Host "  ✓ 核心代码复制完成" -ForegroundColor Green

# 步骤4: 复制示例代码
Write-Host ""
Write-Host "[4/7] 复制示例代码..." -ForegroundColor Yellow

$exampleFiles = @(
  "examples\basic_usage.py",
  "examples\async_usage.py"
)

foreach ($file in $exampleFiles) {
  if (Test-Path $file) {
    Copy-Item -Path $file -Destination "$RELEASE_DIR\$file" -Force
    Write-Host "  ✓ $file" -ForegroundColor Gray
  }
}

# 复制验证脚本
if (Test-Path "test_quick_v013.py") {
  Copy-Item -Path "test_quick_v013.py" -Destination "$RELEASE_DIR\" -Force
  Write-Host "  ✓ test_quick_v013.py" -ForegroundColor Gray
}

Write-Host "  ✓ 示例代码复制完成" -ForegroundColor Green

# 步骤5: 复制文档
Write-Host ""
Write-Host "[5/7] 复制文档..." -ForegroundColor Yellow

$docFiles = @(
  "README.md",
  "ARCHITECTURE.md",
  "CHANGELOG_v0.1.3.md",
  "QUICK_START_v0.1.3.md",
  "SDK_REFACTOR_v0.1.3.md",
  "SIMPLE_USAGE.md",
  "LOCAL_INSTALL_GUIDE.md",
  "LICENSE"
)

foreach ($file in $docFiles) {
  if (Test-Path $file) {
    Copy-Item -Path $file -Destination "$RELEASE_DIR\docs\" -Force
    Write-Host "  ✓ $file" -ForegroundColor Gray
  }
  else {
    Write-Host "  ⚠ 未找到: $file" -ForegroundColor Yellow
  }
}

Write-Host "  ✓ 文档复制完成" -ForegroundColor Green

# 步骤6: 复制配置文件
Write-Host ""
Write-Host "[6/7] 复制配置文件..." -ForegroundColor Yellow

$configFiles = @(
  "setup.py",
  "pyproject.toml",
  "requirements.txt",
  "requirements-dev.txt"
)

foreach ($file in $configFiles) {
  if (Test-Path $file) {
    Copy-Item -Path $file -Destination "$RELEASE_DIR\" -Force
    Write-Host "  ✓ $file" -ForegroundColor Gray
  }
  else {
    Write-Host "  ⚠ 未找到: $file" -ForegroundColor Yellow
  }
}

Write-Host "  ✓ 配置文件复制完成" -ForegroundColor Green

# 步骤7: 构建wheel包（如果可能）
Write-Host ""
Write-Host "[7/7] 构建wheel包..." -ForegroundColor Yellow

try {
  # 检查是否安装了 build 模块
  python -m pip show build | Out-Null
    
  if ($LASTEXITCODE -eq 0) {
    # 构建
    python -m build --wheel --outdir "$RELEASE_DIR\dist"
        
    if ($LASTEXITCODE -eq 0) {
      Write-Host "  ✓ Wheel包构建成功" -ForegroundColor Green
            
      # 复制wheel文件到发布目录根目录
      $wheelFile = Get-ChildItem -Path "$RELEASE_DIR\dist" -Filter "*.whl" | Select-Object -First 1
      if ($wheelFile) {
        Copy-Item -Path $wheelFile.FullName -Destination "$RELEASE_DIR\" -Force
        Write-Host "  ✓ Wheel包已复制到发布目录" -ForegroundColor Green
      }
    }
    else {
      Write-Host "  ⚠ Wheel包构建失败，跳过" -ForegroundColor Yellow
    }
  }
  else {
    Write-Host "  ⚠ 未安装 build 模块，跳过wheel构建" -ForegroundColor Yellow
    Write-Host "    提示: 运行 'pip install build' 安装构建工具" -ForegroundColor Gray
  }
}
catch {
  Write-Host "  ⚠ Wheel包构建失败: $_" -ForegroundColor Yellow
}

# 创建README文件
Write-Host ""
Write-Host "创建发布包README..." -ForegroundColor Yellow

$releaseReadme = @"
# TiMEM Python SDK v${VERSION}

## 📦 发布包内容

此发布包包含 TiMEM Python SDK v${VERSION} 的完整文件。

### 目录结构

``````
timem-python-v${VERSION}/
├── timem/                      # SDK核心代码
│   ├── __init__.py
│   ├── async_client.py         # 异步客户端
│   ├── sync_client.py          # 同步客户端
│   ├── connection_pool.py      # 连接池
│   ├── circuit_breaker.py      # 熔断器
│   ├── monitoring.py           # 监控
│   └── exceptions.py           # 异常定义
├── examples/                   # 示例代码
│   ├── basic_usage.py          # 同步客户端示例
│   └── async_usage.py          # 异步客户端示例
├── docs/                       # 文档
│   ├── README.md               # 项目说明
│   ├── ARCHITECTURE.md         # 架构设计
│   ├── CHANGELOG_v0.1.3.md     # 版本变更
│   ├── QUICK_START_v0.1.3.md   # 快速开始
│   └── ...
├── setup.py                    # 安装配置
├── requirements.txt            # 依赖列表
├── test_quick_v013.py          # 快速验证脚本
└── README.md                   # 本文件
``````

## 🚀 快速安装

### 方式1: 使用wheel包（推荐）

``````bash
pip install timem_python-${VERSION}-py3-none-any.whl
``````

### 方式2: 从源码安装

``````bash
cd timem-python-v${VERSION}
pip install -e .
``````

## ✅ 验证安装

``````bash
# 检查版本
python -c "import timem; print(timem.__version__)"

# 运行验证脚本
python test_quick_v013.py
``````

## 📖 快速开始

### 最简单的例子

``````python
from timem import TiMEMClient

with TiMEMClient(api_key="...", base_url="...") as client:
    # 学习
    result = client.learn(domain="aicv")
    
    # 召回
    rules = client.recall(context={"job_title": "Python工程师"})
    
    # 添加记忆
    memory = client.add_memory(
        user_id=12345,
        domain="test",
        content={"action": "test"}
    )
``````

### 运行示例

``````bash
# 同步客户端示例
python examples/basic_usage.py

# 异步客户端示例
python examples/async_usage.py
``````

## 📚 文档

- **docs/README.md** - 完整使用说明
- **docs/QUICK_START_v0.1.3.md** - 5分钟快速上手
- **docs/ARCHITECTURE.md** - 架构设计文档
- **docs/CHANGELOG_v0.1.3.md** - 版本变更说明

## 🆕 v0.1.3 新特性

### Bug修复
- ✅ 修复 learn() 和 recall() 方法中未定义的 user_id 变量
- ✅ 修复初始化时的配置对象引用问题
- ✅ 改进资源释放逻辑

### 功能增强
- ✨ 统一支持 user_id 监控参数
- ✨ 改进的资源管理
- ✨ 更完善的错误处理

### 文档完善
- 📄 新增完整的架构设计文档
- 📄 新增详细的使用示例
- 📄 新增快速验证脚本

## 📞 技术支持

- Email: contact@aigility.com
- GitHub: https://github.com/AIGility-Cloud-Innovation/timem-python

## 📄 许可证

MIT License

---

**版本**: v${VERSION}  
**发布日期**: 2025-10-23  
**状态**: ✅ 稳定版本
"@

Set-Content -Path "$RELEASE_DIR\README.md" -Value $releaseReadme -Encoding UTF8
Write-Host "  ✓ README.md 已创建" -ForegroundColor Green

# 创建安装说明
$installGuide = @"
# TiMEM Python SDK v${VERSION} 安装指南

## 📋 系统要求

- Python 3.8 或更高版本
- pip 21.0 或更高版本

## 🚀 安装方法

### 方式1: 使用wheel包（推荐）

1. 确保已卸载旧版本：
``````bash
pip uninstall timem-python -y
``````

2. 安装wheel包：
``````bash
pip install timem_python-${VERSION}-py3-none-any.whl
``````

3. 验证安装：
``````bash
python -c "import timem; print(timem.__version__)"
# 应该输出: ${VERSION}
``````

### 方式2: 从源码安装

1. 解压发布包
2. 进入目录：
``````bash
cd timem-python-v${VERSION}
``````

3. 安装依赖：
``````bash
pip install -r requirements.txt
``````

4. 安装SDK：
``````bash
pip install -e .
``````

5. 验证安装：
``````bash
python -c "import timem; print(timem.__version__)"
``````

## ✅ 快速验证

运行验证脚本：
``````bash
python test_quick_v013.py
``````

## 📚 下一步

1. 查看快速开始指南：docs/QUICK_START_v0.1.3.md
2. 运行示例代码：python examples/basic_usage.py
3. 阅读完整文档：docs/README.md

---

如有问题，请查看 docs/ 目录中的文档或联系技术支持。
"@

Set-Content -Path "$RELEASE_DIR\INSTALL.md" -Value $installGuide -Encoding UTF8
Write-Host "  ✓ INSTALL.md 已创建" -ForegroundColor Green

# 创建压缩包
Write-Host ""
Write-Host "正在创建ZIP压缩包..." -ForegroundColor Yellow

try {
  # 使用 PowerShell 的 Compress-Archive
  $zipPath = "${RELEASE_NAME}.zip"
    
  # 删除已存在的zip文件
  if (Test-Path $zipPath) {
    Remove-Item -Path $zipPath -Force
  }
    
  # 压缩整个发布目录
  Compress-Archive -Path "$RELEASE_DIR\*" -DestinationPath $zipPath -CompressionLevel Optimal
    
  Write-Host "  ✓ ZIP压缩包创建成功" -ForegroundColor Green
    
  # 获取文件大小
  $zipFile = Get-Item $zipPath
  $fileSizeMB = [math]::Round($zipFile.Length / 1MB, 2)
    
  Write-Host ""
  Write-Host "=" * 70 -ForegroundColor Cyan
  Write-Host "  ✅ 打包完成！" -ForegroundColor Green
  Write-Host "=" * 70 -ForegroundColor Cyan
  Write-Host ""
  Write-Host "发布包信息：" -ForegroundColor Cyan
  Write-Host "  版本：v${VERSION}" -ForegroundColor White
  Write-Host "  文件：${zipPath}" -ForegroundColor White
  Write-Host "  大小：${fileSizeMB} MB" -ForegroundColor White
  Write-Host "  目录：$RELEASE_DIR" -ForegroundColor White
  Write-Host ""
  Write-Host "发布包内容：" -ForegroundColor Cyan
  Write-Host "  ✓ SDK核心代码 (timem/)" -ForegroundColor White
  Write-Host "  ✓ 示例代码 (examples/)" -ForegroundColor White
  Write-Host "  ✓ 完整文档 (docs/)" -ForegroundColor White
  Write-Host "  ✓ 配置文件 (setup.py, requirements.txt)" -ForegroundColor White
  Write-Host "  ✓ 验证脚本 (test_quick_v013.py)" -ForegroundColor White
  Write-Host "  ✓ 安装指南 (INSTALL.md)" -ForegroundColor White
    
  if (Test-Path "$RELEASE_DIR\*.whl") {
    Write-Host "  ✓ Wheel安装包 (*.whl)" -ForegroundColor White
  }
    
  Write-Host ""
  Write-Host "下一步操作：" -ForegroundColor Cyan
  Write-Host "  1. 解压: Expand-Archive -Path ${zipPath} -DestinationPath ." -ForegroundColor Gray
  Write-Host "  2. 安装: pip install timem_python-${VERSION}-py3-none-any.whl" -ForegroundColor Gray
  Write-Host "  3. 验证: python test_quick_v013.py" -ForegroundColor Gray
  Write-Host ""
    
}
catch {
  Write-Host "  ✗ ZIP压缩失败: $_" -ForegroundColor Red
  exit 1
}

# 生成发布说明
Write-Host "生成发布说明..." -ForegroundColor Yellow

$releaseNotes = @"
# TiMEM Python SDK v${VERSION} 发布说明

## 📦 发布包

- **文件名**: ${RELEASE_NAME}.zip
- **版本**: v${VERSION}
- **发布日期**: $(Get-Date -Format "yyyy-MM-dd")
- **大小**: ${fileSizeMB} MB

## 🎯 本次发布重点

### Bug修复
- ✅ 修复 learn() 方法中未定义的 user_id 变量
- ✅ 修复 recall() 方法中未定义的 user_id 变量
- ✅ 修复初始化时的配置对象引用问题
- ✅ 改进资源释放逻辑

### 功能增强
- ✨ 统一支持 user_id 监控参数
- ✨ 改进的资源管理和错误处理
- ✨ 更完善的日志记录

### 文档完善
- 📄 ARCHITECTURE.md - 完整的架构设计文档
- 📄 CHANGELOG_v0.1.3.md - 详细的版本变更日志
- 📄 QUICK_START_v0.1.3.md - 5分钟快速上手指南
- 📄 SDK_REFACTOR_v0.1.3.md - 重构总结文档

### 示例代码
- 📝 examples/basic_usage.py - 同步客户端完整示例
- 📝 examples/async_usage.py - 异步客户端完整示例
- 🧪 test_quick_v013.py - 快速验证脚本

## 📊 版本对比

| 特性 | v0.1.2 | v0.1.3 |
|------|--------|--------|
| 核心bug | ❌ 有3个 | ✅ 已修复 |
| user_id支持 | ❌ 无 | ✅ 完整支持 |
| 使用示例 | ❌ 无 | ✅ 完整 |
| 架构文档 | ❌ 无 | ✅ 详细 |
| 生产就绪 | ❌ 否 | ✅ 是 |

## 🚀 快速安装

``````bash
# 1. 解压发布包
Expand-Archive -Path ${RELEASE_NAME}.zip

# 2. 安装
pip install ${RELEASE_NAME}/timem_python-${VERSION}-py3-none-any.whl

# 3. 验证
python -c "import timem; print(timem.__version__)"
``````

## 📚 文档

- **INSTALL.md** - 安装指南
- **docs/README.md** - 完整文档
- **docs/QUICK_START_v0.1.3.md** - 快速开始
- **docs/ARCHITECTURE.md** - 架构设计
- **docs/CHANGELOG_v0.1.3.md** - 版本变更

## ⚠️ 升级提示

从 v0.1.2 升级到 v0.1.3：

1. 卸载旧版本：
``````bash
pip uninstall timem-python -y
``````

2. 清理缓存：
``````bash
pip cache purge
``````

3. 安装新版本：
``````bash
pip install timem_python-${VERSION}-py3-none-any.whl
``````

4. 验证版本：
``````bash
python -c "import timem; print(timem.__version__)"
``````

## ✅ 验证清单

- [ ] 已安装 Python 3.8+
- [ ] 已卸载旧版本
- [ ] 已安装 v${VERSION}
- [ ] 版本号显示正确
- [ ] 运行 test_quick_v013.py 通过
- [ ] 运行示例代码成功

## 📞 技术支持

如有问题，请联系：
- Email: contact@aigility.com
- GitHub: https://github.com/AIGility-Cloud-Innovation/timem-python

---

**发布时间**: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")  
**SDK版本**: v${VERSION}  
**状态**: ✅ 稳定版本，推荐使用
"@

Set-Content -Path "${RELEASE_NAME}_RELEASE_NOTES.md" -Value $releaseNotes -Encoding UTF8
Write-Host "  ✓ 发布说明已生成: ${RELEASE_NAME}_RELEASE_NOTES.md" -ForegroundColor Green

Write-Host ""
Write-Host "=" * 70 -ForegroundColor Green
Write-Host "  🎉 打包流程全部完成！" -ForegroundColor Green
Write-Host "=" * 70 -ForegroundColor Green
Write-Host ""

