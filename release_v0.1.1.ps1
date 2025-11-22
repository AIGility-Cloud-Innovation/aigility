# TiMem-Python v0.1.1 发布脚本
# 使用方法: .\release_v0.1.1.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "TiMem-Python v0.1.1 发布脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查是否在 git 仓库中
if (-not (Test-Path .git)) {
  Write-Host "错误: 当前目录不是 git 仓库" -ForegroundColor Red
  exit 1
}

# 检查是否有未提交的更改
$status = git status --porcelain
if ($status) {
  Write-Host "警告: 检测到未提交的更改:" -ForegroundColor Yellow
  Write-Host $status -ForegroundColor Yellow
  Write-Host ""
  $confirm = Read-Host "是否继续发布? (y/N)"
  if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host "发布已取消" -ForegroundColor Yellow
    exit 0
  }
}

# 验证版本号
Write-Host "1. 验证版本号..." -ForegroundColor Green
$pyprojectVersion = Select-String -Path "pyproject.toml" -Pattern 'version = "([^"]+)"' | ForEach-Object { $_.Matches.Groups[1].Value }
$initVersion = Select-String -Path "timem\__init__.py" -Pattern '__version__ = "([^"]+)"' | ForEach-Object { $_.Matches.Groups[1].Value }

if ($pyprojectVersion -ne "0.1.1") {
  Write-Host "错误: pyproject.toml 中的版本号不是 0.1.1 (当前: $pyprojectVersion)" -ForegroundColor Red
  exit 1
}

if ($initVersion -ne "0.1.1") {
  Write-Host "错误: timem/__init__.py 中的版本号不是 0.1.1 (当前: $initVersion)" -ForegroundColor Red
  exit 1
}

Write-Host "   ✓ 版本号验证通过: 0.1.1" -ForegroundColor Green
Write-Host ""

# 提交更改
Write-Host "2. 提交版本更新..." -ForegroundColor Green
git add pyproject.toml timem/__init__.py CHANGELOG.md
$commitMessage = "chore: bump version to 0.1.1"
git commit -m $commitMessage

if ($LASTEXITCODE -ne 0) {
  Write-Host "   ⚠ 提交可能失败或无更改" -ForegroundColor Yellow
}
else {
  Write-Host "   ✓ 版本更新已提交" -ForegroundColor Green
}
Write-Host ""

# 推送到远程
Write-Host "3. 推送到远程仓库..." -ForegroundColor Green
$confirm = Read-Host "是否推送到远程仓库? (y/N)"
if ($confirm -eq "y" -or $confirm -eq "Y") {
  git push origin main
  if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✓ 代码已推送到远程" -ForegroundColor Green
  }
  else {
    Write-Host "   ✗ 推送失败" -ForegroundColor Red
    exit 1
  }
}
else {
  Write-Host "   ⏭ 跳过推送" -ForegroundColor Yellow
}
Write-Host ""

# 创建并推送标签
Write-Host "4. 创建并推送标签 v0.1.1..." -ForegroundColor Green
$tagExists = git tag -l "v0.1.1"
if ($tagExists) {
  Write-Host "   ⚠ 标签 v0.1.1 已存在" -ForegroundColor Yellow
  $confirm = Read-Host "是否删除并重新创建? (y/N)"
  if ($confirm -eq "y" -or $confirm -eq "Y") {
    git tag -d v0.1.1
    git push origin :refs/tags/v0.1.1
  }
  else {
    Write-Host "   ⏭ 跳过标签创建" -ForegroundColor Yellow
    exit 0
  }
}

$confirm = Read-Host "是否创建并推送标签 v0.1.1? (y/N)"
if ($confirm -eq "y" -or $confirm -eq "Y") {
  git tag -a v0.1.1 -m "Release v0.1.1 - Memory management enhancements"
  git push origin v0.1.1
    
  if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✓ 标签已创建并推送" -ForegroundColor Green
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "发布流程已启动！" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "GitHub Actions 将自动:" -ForegroundColor Yellow
    Write-Host "  1. 检测到 v0.1.1 标签" -ForegroundColor Yellow
    Write-Host "  2. 构建包" -ForegroundColor Yellow
    Write-Host "  3. 发布到 PyPI" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "查看发布状态:" -ForegroundColor Cyan
    Write-Host "  https://github.com/YOUR_REPO/actions" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "发布成功后，等待几分钟后可以安装:" -ForegroundColor Cyan
    Write-Host "  pip install --upgrade timem-ai" -ForegroundColor Cyan
  }
  else {
    Write-Host "   ✗ 标签推送失败" -ForegroundColor Red
    exit 1
  }
}
else {
  Write-Host "   ⏭ 跳过标签创建" -ForegroundColor Yellow
  Write-Host ""
  Write-Host "提示: 您可以稍后手动创建标签:" -ForegroundColor Yellow
  Write-Host "  git tag -a v0.1.1 -m 'Release v0.1.1'" -ForegroundColor Yellow
  Write-Host "  git push origin v0.1.1" -ForegroundColor Yellow
}

