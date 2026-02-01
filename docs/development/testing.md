# Testing

This page is aligned with the repository `tests/README.md` and covers the common commands for running unit and integration tests locally.

- Tests are executed in a Python virtual environment (`venv`). Create and activate a virtual environment before running tests:

```bash
python -m venv venv

source venv/bin/activate  # On Windows: venv\Scripts\activate
```

- Install test dependencies (from the project root in the activated venv):

```bash
python -m pip install -e ".[develop]"
```

- Run all tests:

```bash
pytest
```

- Run with coverage and HTML report:

```bash
pytest --cov=octoprint_uptime --cov-report=html
```

- Run a single test file or test:

```bash
pytest tests/plugin_test.py::test_some_case -q
```

## Writing tests

- Use `pytest` and mock external dependencies where possible.
- Keep unit tests fast and deterministic (prefer `monkeypatch` over sleeps).
