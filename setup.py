import os
from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), "requirements.lock"), 'r', encoding='utf-8') as f:
    dependencies = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="FaultSeeker",
    author="Kairan Sun",
    description="An AI-powered tool for automated fault localization in malicious blockchain transactions.",
    packages=find_packages(include=["faultseeker", "faultseeker.*"]),
    install_requires=dependencies,
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "faultseeker=faultseeker.main:main_cli",
        ]
    },
)
