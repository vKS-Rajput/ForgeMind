## What
<!-- One sentence: what does this PR do? -->

## Why
<!-- One sentence: why is this change needed? -->

## How
<!-- Brief technical description of the approach -->

## Checklist

- [ ] Tests added/updated
- [ ] Type hints on all new public functions
- [ ] Docstrings on all new public functions
- [ ] No new `# type: ignore` without justification comment
- [ ] Architectural boundaries preserved (no forbidden imports)
- [ ] ADR created/updated if architectural decision was made
- [ ] CI passes locally: `uv run pytest && uv run ruff check . && uv run mypy src/`
