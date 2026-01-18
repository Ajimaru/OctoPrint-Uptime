# Test Suite

This directory contains the test suite for your OctoPrint plugin. The template ships without test files—add unit and integration tests as you build features.

## Running Tests

Install test dependencies:

```bash
pip install -e ".[develop]"
```

Run all tests:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=octoprint_plugin_template --cov-report=html
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

Refer to OctoPrint's [plugin development documentation](https://docs.octoprint.org/en/latest/plugins/development.html#testing) for more details.
