# GitHub Copilot Instructions - OctoPrint Plugin Template

**Issue**: https://github.com/OctoPrint/OctoPrint/issues/4355
**Target**: OctoPrint 1.12.0+, Python 3.10+ | Implements 2021 feature request

## Code Standards (CRITICAL)

**Docs**: https://docs.octoprint.org/en/main/plugins/index.html | Contributing: https://github.com/OctoPrint/OctoPrint/blob/main/CONTRIBUTING.md

**Template Autoescape**: [How do I improve my plugin's security by enabling autoescape?](https://faq.octoprint.org/plugin-autoescape)

### Code Style (OctoPrint Standard)

- **Indentation**: 4 spaces (NO TABS)
- **Language**: English only (code, comments, docs)
- **Docstrings**: All public methods/classes
- **Comments**: Explain WHY, not WHAT
- **Line length**: 120 chars max (black)
- **No dead code**: Remove all commented-out experiments
- **Import order**: stdlib → third-party → octoprint → local

### Repository communication (English only)

### change /CHANGELOG.md only on order

- **All public-facing repository communication must be in English only**: GitHub Issues, Pull Requests, Discussions, Wiki pages, and Security advisories.
- If a user writes in another language, respond in English and keep technical terms consistent.

**When generating code**: Follow OctoPrint standards, use English, include docstrings, test edge cases, ensure thread safety, keep performance in mind. Prefer modular, easily replaceable placeholders for new plugins.

### Testing: pytest, min 70% coverage, test edge cases, mock OctoPrint internals

### Thread Safety (CRITICAL)

### Logging (use self.\_logger)

```python
self._logger.info("Plugin loaded")
self._logger.debug("Config: %s", self._settings.get_all_data())
self._logger.error("Failed: %s", str(e))
```

## Internationalization

**Babel Translation**:

```bash
pybabel extract -F babel.cfg -o translations/messages.pot .
pybabel init -i translations/messages.pot -d translations -l de
pybabel compile -d translations
```

**Languages**: English (en) + German (de) (extend as needed)

## Critical Rules

1. **DO NOT** use `print()` → use `self._logger`
2. **DO NOT** edit CSS directly → Edit LESS and compile
3. **DO NOT** block callbacks → Keep them fast (<10ms) when tied to OctoPrint events
4. **DO NOT** forget thread safety → Use locks for shared data
5. **DO NOT** use globals → Use instance variables only
6. **DO NOT** hardcode strings → Use i18n for user-facing text
7. **DO NOT** ship dead code → Remove experiments

## Performance

- Keep callbacks lightweight (<10ms when subscribed to frequent events)
- Avoid large in-memory histories; prune regularly

## Development Workflow

```bash
# Branch: wip/feature-name or fix/issue-description
# Commit: "Add feature" (imperative mood)
# Before commit: pytest && pre-commit run --all-files
```

## Files to Ignore (Don't Commit)

`.development/`, `venv/`, `__pycache__/`, `.pytest_cache/`, `.coverage/`, `.idea/`, `.vscode/`, `dist/`, `build/`, `*.egg-info/`

## Key References

- Plugin Docs: https://docs.octoprint.org/en/main/plugins/index.html
- Mixins: https://docs.octoprint.org/en/main/plugins/mixins.html
- Contributing: https://github.com/OctoPrint/OctoPrint/blob/main/CONTRIBUTING.md
- Knockout.js: https://knockoutjs.com/documentation/introduction.html
- Implementation Plan: .ideas/IMPLEMENTATION_PLAN.md
