"""
AIGility ADK Setup Script
"""

from setuptools import setup, find_packages

# 读取 README
try:
    with open("adk/README.md", "r", encoding="utf-8") as f:
        long_description = f.read()
except FileNotFoundError:
    long_description = "AIGility ADK - Agent Development Kit"

setup(
    name="aigility-adk",
    version="0.0.1",
    description="AIGility ADK - Agent Development Kit | 基于 LangGraph/LangChain 的智能体开发框架",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="AIGility Cloud Innovation",
    author_email="contact@aigility.com",
    url="https://github.com/AIGility-Cloud-Innovation/aigility-adk",
    packages=find_packages(include=["adk*"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8",
    install_requires=[
        "httpx>=0.24.0",
        "pydantic>=2.0.0",
        "typing-extensions>=4.0.0",
        "langchain>=0.1.0",
        "langgraph>=0.0.20",
        "langchain-openai>=0.0.5",
        "langchain-anthropic>=0.1.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "isort>=5.0.0",
            "flake8>=5.0.0",
            "mypy>=1.0.0",
            "pre-commit>=2.20.0",
        ],
        "docs": [
            "sphinx>=5.0.0",
            "sphinx-rtd-theme>=1.0.0",
            "myst-parser>=0.18.0",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)

