# 快速更新和测试脚本
Write-Host "`n更新SDK..." -ForegroundColor Cyan
pip uninstall timem-python -y 2>&1 | Out-Null
pip install dist\timem_python-0.1.3-py3-none-any.whl --force-reinstall

Write-Host "`n验证版本..." -ForegroundColor Cyan
python -c "import timem; print(f'SDK版本: {timem.__version__}')"

Write-Host "`n运行记忆测试..." -ForegroundColor Cyan
python examples/test_memory.py

