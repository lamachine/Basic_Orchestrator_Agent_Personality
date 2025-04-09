from setuptools import setup, find_packages

setup(
    name="basic_orchestrator_agent",
    version="0.1.0",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "pydantic",
        "langgraph",
        "supabase",
    ],
    extras_require={
        "dev": [
            "pytest",
            "pytest-asyncio",
            "pytest-cov",
            "black",
            "isort",
        ],
    },
) 