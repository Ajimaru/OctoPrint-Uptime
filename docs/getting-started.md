# Getting started

- Install docs dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements-docs.txt
```

- Generate JS docs (if desired):

```bash
npm install --save-dev jsdoc jsdoc-to-markdown
./scripts/generate-jsdocs.sh
```

- Serve docs locally:

```bash
mkdocs serve
```

## Notes

This document is contributor-focused and omits end-user installation guidance such as package dependencies. For user-facing instructions about uptime dependencies (for example how to install `psutil` in your OctoPrint virtualenv), see the `Installation` and `Dependencies` sections in the project README.
