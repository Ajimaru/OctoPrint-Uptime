# Test Suite

This directory contains the test suite for the OctoPrint plugin.

## Documentation

View detailed diagrams and documentation for the test suite:

→ **[Testing - Diagrams and Documentation](../docs/development/testing-diagrams.md)**

This includes a comprehensive overview of all test categories, coverage areas, and test flows.

---

## Running Tests

- Tests are executed in a Python virtual environment (`venv`). Create and activate a virtual environment before running tests:

```bash
python -m venv venv

source venv/bin/activate  # On Windows: venv\Scripts\activate
```

- Install test dependencies in the virtual environment:

```bash
pip install -e ".[develop]"
```

- Run all tests:

```bash
pytest
```

- Run with coverage:

```bash
pytest --cov=octoprint_uptime --cov-report=html
```

## Writing Tests

Follow OctoPrint's testing guidelines:

- Use pytest for new tests
- Ensure good code coverage
- Test edge cases
- Mock external dependencies
- Run unit tests
- Check code coverage (aim for >70%)
- Performance profiling

### Unit Tests

Add unit tests under `tests/` as you build out your plugin. Keep tests focused and fast; prefer deterministic tests using `monkeypatch` over real sleeps.

### Integration Tests

- **Virtual Printer:** Manual testing with OctoPrint's Virtual Printer plugin
- **Real Printer:** Beta testing with a real printer
- **Browser Testing:** Chrome, Firefox, Safari
