from setuptools import setup, find_packages

# Read the contents of README file
with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="mulesoft-flow-analyzer",
    version="1.1.1",
    author="Brad McNaughton",
    author_email="hello@bradmcnaughton.com",
    description="A tool for analyzing MuleSoft integration projects to generate sequence diagrams or natural language descriptions of each flow",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/bradmcnaughton/mulesoft-flow-analyzer",
    project_urls={
        "Bug Tracker": "https://github.com/bradmcnaughton/mulesoft-flow-analyzer/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.8",
    install_requires=[
        "xmltodict",
        "pyyaml",
        "plantweb",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov",
        ],
    },
)