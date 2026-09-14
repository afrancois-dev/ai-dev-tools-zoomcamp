# Repository Instructions

- The repository now contains the minimal Django project in `config/`, the initial application in `core/`, and the management entrypoint in `manage.py`; `main.py` remains the original starter smoke script.
- Use Python `>=3.13` and manage dependencies with `uv`; keep `pyproject.toml` and `uv.lock` synchronized when dependencies change.
- The verified smoke command is `uv run python main.py`.
- Run the Django test suite with `uv run python manage.py test`; no linter, formatter, type checker, CI workflow, or code-generation command is configured yet.
- `_docs/plan.md` is the product and architecture scope: the intended implementation is Django templates + HTMX, PostgreSQL, and Docker/Docker Compose.
- `_docs/backlog.md` is the ordered implementation backlog; issue numbers correspond to GitHub issues in the repository.
- `README.md` is intentionally empty as part of the homework setup; do not treat its lack of instructions as evidence that setup is complete.

Commands

- `uv sync` - install dependencies
- `uv run pytest` - the whole suite
- `uv run pytest tests/test_home.py` - one test file

Rules

- Dependencies are added in `pyproject.toml`. Do not add one without
  asking

Documents

- `_docs/process.md` - how work is organized
- Before writing tests, read `_docs/testing-guidelines.md`
- For anything touching the UI, read `_docs/design-system.md`
- For any commit, use the following convention _docs/commit-template.md