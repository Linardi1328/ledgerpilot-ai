# Contributing

LedgerPilot AI uses review branches and independent review for all meaningful changes.

```text
main
  |
  v
review/<phase-or-task>
  |
  v
implementation
  |
  v
verification
  |
  v
push
  |
  v
pull request
  |
  v
independent review
  |
  v
owner approval
  |
  v
merge
```

## Branching Rules

- Do not perform normal development directly on `main`.
- Use one review branch per phase or focused change.
- Keep commits focused and reviewable.
- Do not merge automatically.
- Do not begin a later phase until the owner has approved the prior phase.

## Verification Rules

Run the relevant checks before marking work complete:

```bash
python -m pytest
python -m ruff check .
python -m mypy src
python -c "import ledgerpilot"
```

When configured, also run:

```bash
python -m pytest --cov
python -m ruff format --check .
python -m build
```

## Sensitive Data Rules

- Commit synthetic development data only.
- Never commit real client records, invoices, receipts, bank details, taxpayer identifiers, MyInvois identifiers, or employee information.
- Never commit `.env` files, API keys, tokens, passwords, private certificates, or production databases.
- Review `git status`, `git diff`, `git diff --cached`, tracked files, and credential-like strings before pushing.

Passing tests do not override the sensitive-data review requirement.
