from setuptools import setup, find_packages

setup(
    name="agent-reasoning",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests",
        "termcolor",
        "fastapi",
        "uvicorn"
    ],
)
