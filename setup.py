from setuptools import setup, find_packages

setup(
    name="volttron_installer",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.111.1",
        "reflex>=0.6.8",
        "ansible>=10.2.0",
        "httpx>=0.27.0",
    ],
    extras_require={
        "dev": [
            "pytest>=8.1.1",
            "pytest-asyncio>=0.23.5",
            "pytest-mock>=3.12.0",
        ],
    },
)
