# GitHub Copilot Instructions - OctoPrint Plugin Template

## Key References

**Issue** <https://github.com/OctoPrint/OctoPrint/issues/4355>

**Target** OctoPrint 1.12.0+, Python 3.7+ | Implements 2021 feature request

**Docs** <https://docs.octoprint.org/en/main/plugins/index.html>

**Contributing** <https://github.com/OctoPrint/OctoPrint/blob/main/CONTRIBUTING.md>

**Mixins** <https://docs.octoprint.org/en/main/plugins/mixins.html>

**Knockout.js** <https://knockoutjs.com/documentation/introduction.html>

**Template Autoescape**: [How do I improve my plugin's security by enabling autoescape?](https://faq.octoprint.org/plugin-autoescape)

## Code Style (OctoPrint Standard)

- **Indentation**: 4 spaces (NO TABS)
- **Language**: English only (code, comments, docs)
- **Docstrings**: All public methods/classes
- **Comments**: Explain WHY, not WHAT
- **Line length**: 100 chars max (black)
- **No dead code**: Remove all commented-out experiments
- **Import order**: stdlib → third-party → octoprint → local
- **All public-facing repository communication must be in English only**: GitHub Issues, Pull Requests, Discussions, Wiki pages, and Security advisories.

## Testing

- pytest, min 70% coverage
- test edge cases
- mock OctoPrint internals

## Logging

**use self.\_logger**

```python
self._logger.info("Plugin loaded")
self._logger.debug("Config: %s", self._settings.get_all_data())
self._logger.error("Failed: %s", str(e))
```

## Internationalization

**Languages** English (en) + German (de) (extend as needed)

**Babel Translation**

```bash
pybabel extract -F babel.cfg -o translations/messages.pot .
pybabel init -i translations/messages.pot -d translations -l de
pybabel compile -d translations
```

## Files to Ignore (Don't Commit)

`.development/`, `venv/`, `__pycache__/`, `.pytest_cache/`, `.coverage/`, `.idea/`, `.vscode/`, `dist/`, `build/`, `*.egg-info/`
