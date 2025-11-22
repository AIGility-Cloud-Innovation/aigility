.PHONY: help install install-dev test lint format clean build docs

help:
	@echo "AIGility ADK - 开发命令"
	@echo ""
	@echo "可用命令:"
	@echo "  make install       - 安装依赖"
	@echo "  make install-dev   - 安装开发依赖"
	@echo "  make test          - 运行测试"
	@echo "  make lint          - 代码检查"
	@echo "  make format        - 代码格式化"
	@echo "  make clean         - 清理构建文件"
	@echo "  make build         - 构建包"
	@echo "  make docs          - 生成文档"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pre-commit install

test:
	pytest tests/ -v --cov=adk --cov-report=html

lint:
	flake8 adk/ tests/
	mypy adk/

format:
	black adk/ tests/
	isort adk/ tests/

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .coverage htmlcov/
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete

build:
	python -m build

docs:
	cd docs && make html

