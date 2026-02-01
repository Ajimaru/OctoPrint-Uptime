# Testing — Diagrams and Documentation

This section contains detailed diagrams and documentation for the test suite of the OctoPrint-Uptime plugin.

## Test Suite Overview

- **[Test Suite Overview](testing-diagrams/index.html)** — Complete overview page with links to all diagrams
- **[plugin_test.py](testing-diagrams/plugin-tests.html)** — Complete overview of all test categories, including:
  - Utility function tests (uptime formatting)
  - Settings validation and sanitization tests
  - Logging and debug throttling tests
  - Uptime retrieval tests (/proc/uptime, psutil)
  - API endpoint tests with permissions
  - Hook inspection and safe invocation tests
  - Plugin reload and dependency handling tests

## Test Categories

The test suite is organized into the following categories:

### 1. **Utility Functions** (`test_format_uptime_*`)

Tests for uptime formatting utilities with various time unit combinations.

### 2. **Settings** (`test_validate_and_sanitize_*`, `test_log_settings_*`)

Tests for settings validation, data structure checks, and default value handling.

### 3. **Logging** (`test_log_debug_*`)

Tests for debug throttling, exception handling, and logging behavior.

### 4. **Uptime Retrieval** (`test_get_uptime_*`)

Tests for retrieving uptime from `/proc/uptime`, `psutil`, boot time handling, and error cases.

### 5. **API** (`test_on_api_get*`, `test_fallback_uptime_*`)

Tests for Flask integration, permission checks, JSON responses, and error handling.

### 6. **Hooks** (`test_hook_inspection_*`, `test_on_settings_*`)

Tests for OctoPrint hook detection, safe invocation, and parameter validation.

### 7. **Plugin Reload** (`test_reload_*`)

Tests for module reloading, dependency checking, and fallback handling.

## Running Tests

```bash
# Activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install test dependencies
pip install -e ".[develop]"

# Run all tests
pytest

# Run with coverage report
pytest --cov=octoprint_uptime --cov-report=html

# Run specific test category
pytest tests/plugin_test.py::test_format_uptime_variants
```

## Coverage Goals

- **Target:** > 70% code coverage
- **Current:** See `coverage.xml` in the repository root
- **Report:** Generate with `pytest --cov-report=html`

---

For more information, see [Testing Documentation](testing.md).
