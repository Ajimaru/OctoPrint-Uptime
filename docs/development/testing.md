# Testing

This page is aligned with the repository `tests/README.md` and covers the common commands for running unit and integration tests locally.

Install test dependencies (from the project root):

```bash
python -m pip install -e ".[develop]"
```

Run all tests:

```bash
pytest
```

Run with coverage and HTML report:

```bash
pytest --cov=octoprint_uptime --cov-report=html
```

Run a single test file or test:

```bash
pytest tests/test_uptime.py::test_some_case -q
```

## Writing tests

- Use `pytest` and mock external dependencies where possible.
- Keep unit tests fast and deterministic (prefer `monkeypatch` over sleeps).
