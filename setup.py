from setuptools import setup, find_packages

setup(
    name="glass-optimizer",
    version="0.1.0",
    description="Endustriyel cam kesim optimizasyon paketi (OR-Tools CP-SAT)",
    author="Anil Akpunar",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.9",
    install_requires=[
        "ortools>=9.8.3296",
        "matplotlib>=3.7.0",
        "numpy>=1.24.0",
        "pandas>=2.0.0",
        "pydantic>=2.5.0",
        "rich>=13.7.0",
        "typer>=0.9.0",
    ],
    entry_points={
        "console_scripts": [
            "glass-optimize=glass_optimizer.presentation.cli:app",
        ],
    },
)
