# Releasing to PyPI

This document describes how to publish **mule-flow-analyzer** for the first time and for subsequent releases.

## Prerequisites

- A [PyPI](https://pypi.org/account/register/) account (and optionally [Test PyPI](https://test.pypi.org/account/register/) for a dry run).
- Python 3.8+ with the project installed in development mode:

  ```bash
  pip install -e ".[dev]"
  ```

  The `dev` extra includes `build` and `twine`.

## One-time PyPI setup

1. **Choose an upload method**
   - **Trusted publishing (recommended)**  
     In the PyPI project settings, add a *trusted publisher* for this GitHub repository (and workflow/environment if you use OIDC). Then configure a GitHub Actions job that uploads on tag push without storing long-lived API tokens. See [PyPI: Trusted publishers](https://docs.pypi.org/trusted-publishers/).
   - **API token**  
     Create an API token on PyPI, store it as a secret (for example `PYPI_API_TOKEN`), and use `twine upload` with `TWINE_USERNAME=__token__` and `TWINE_PASSWORD=<token>`.

2. **Ensure metadata is correct** in `pyproject.toml`: `version`, `readme`, `license`, `[project.urls]`, and classifiers.

## Dry run on Test PyPI

```bash
python -m build
twine check dist/*
twine upload --repository testpypi dist/*
```

Install from Test PyPI (use `--index-url` only for this test):

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ mule-flow-analyzer
```

## Release to PyPI

1. Bump the version in:
   - `pyproject.toml` (`[project]` `version`)
   - `src/mule_flow_analyzer/__init__.py` (`__version__`)

2. Commit the version bump and tag (example):

   ```bash
   git tag v1.0.1
   git push origin v1.0.1
   ```

3. Build and upload:

   ```bash
   rm -rf dist build *.egg-info
   python -m build
   twine check dist/*
   twine upload dist/*
   ```

4. Confirm the [PyPI project page](https://pypi.org/project/mule-flow-analyzer/) shows the new version and that `pip install mule-flow-analyzer` installs it.

## Versioning policy

Keep **one logical version** across `pyproject.toml` and `__init__.py` for every release. Use [semantic versioning](https://semver.org/) (MAJOR.MINOR.PATCH) as appropriate for API and behavior changes.
