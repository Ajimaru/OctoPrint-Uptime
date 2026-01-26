# Contributing

This page summarizes the contributor workflow for developers. The authoritative, repository-wide contributor guidance is in the top-level `CONTRIBUTING.md` — keep both in sync.

Quickstart

- Create and activate a virtual environment and install development deps:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[develop]"
```

If you prefer helper scripts, run the repository helper to set up a dev environment:

```bash
bash .development/setup_dev.sh
```

Branches & PRs

- Create a feature branch and open a PR into `main` (direct pushes to `main` are blocked).
- One logical change per PR; include testing notes and screenshots for UI changes.

Pre-commit

- We use `pre-commit` hooks. To run all hooks locally:

```bash
pre-commit run --hook-stage manual --all-files
```

Internationalization

- Follow the i18n instructions in `CONTRIBUTING.md` when adding or changing strings (use `pybabel extract`, `update`, `compile`).

Notes

- Keep changes small and focused. Follow the coding style in `CONTRIBUTING.md` (4-space indentation, English text, use `self._logger` for logging).
