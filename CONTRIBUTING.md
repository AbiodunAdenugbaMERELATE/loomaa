# Contributing to Loomaa

Thanks for taking the time to contribute.

## Quickstart (local dev)

Prereqs:
- Python 3.8+
- Git

Setup:

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate

pip install -r requirements.txt
pytest -q
```

## Project structure

- `loomaa/` – package code (CLI/compiler/deploy/viewer)
- `tests/` – unit tests
- `setup.py` – packaging metadata and runtime dependencies

## Running locally

Common commands:

- Run tests: `pytest -q`
- Editable install (already done by `requirements.txt`): `pip install -e .`

## Pull request checklist

Before opening a PR:
- Run `pytest -q`
- Keep changes focused and small
- Add/adjust tests when you change behavior
- Update the README if you change CLI behavior

## Security

- Never commit secrets: `.env`, client secrets, tokens, tenant/workspace IDs.
- Use `.env.example` or the `loomaa init` scaffold for documentation.

## Release notes (maintainers)

- Bump version in `setup.py`
- Build: `python -m build`
- Check: `python -m twine check dist/*`
- Upload: `python -m twine upload dist/*`
