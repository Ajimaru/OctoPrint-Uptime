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

Uptime dependency note

---

The plugin uses `/proc/uptime` on Linux and `psutil` when available. For non-Linux systems or virtualenvs without `psutil`, uptime may not be available. To add `psutil` to your OctoPrint virtualenv:

```bash
venv/bin/pip install psutil
```

If you manage OctoPrint via a system package or Docker image, follow your installation method to add `psutil` in the environment where OctoPrint runs.
