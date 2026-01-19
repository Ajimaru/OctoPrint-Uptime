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
