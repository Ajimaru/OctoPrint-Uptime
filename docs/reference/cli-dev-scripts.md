# CLI / Dev helper scripts

## JS documentation generation

The repository provides an automated JSDoc → Markdown step integrated into pre-commit. The `jsdoc-gen` hook runs `./scripts/generate-jsdocs.sh`. To make local commits faster the hook passes only changed filenames to the script (`pass_filenames: true`) and the script documents only the files it receives. When running the script manually it still documents the whole package if no filenames are given.

Notes:

- These scripts are convenience helpers and are not a shield against manual verification. Always run tests (`pytest`) and check the generated artifacts before publishing.
