# Contributing

Thanks for helping improve Embedding Cache Inspector.

## Development

This project intentionally uses only the Python standard library at runtime.

```bash
python -m unittest discover -s tests
```

## Guidelines

- Keep runtime dependencies at zero unless there is a strong reason to change the project goal.
- Add tests for loader, audit, reporter, and CLI behavior when changing those areas.
- Do not commit virtual environments, generated reports, build outputs, local databases, or secrets.
- Prefer small, focused pull requests with clear reproduction steps.

## Security

Do not include real API keys, database credentials, customer documents, or private embeddings in fixtures. Use synthetic data only.
