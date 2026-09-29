# Contributing to repo-factory

Thanks for considering a contribution.

## Development

```bash
git clone https://github.com/theworker02/repo-factory.git
cd repo-factory
node --test
node src/cli.js
```

## Guidelines

1. Keep the toolkit **zero-dependency** unless there is a compelling, discussed reason.
2. Preserve the `run(argv)` contract or propose a major-version bump.
3. Update `CHANGELOG.md` for user-visible changes.
4. Keep the docs site in `docs/` coherent with README examples.
5. Do not commit secrets, credentials, or large binaries.

## Pull requests

- Prefer small, reviewable PRs.
- Include a short test or sample invocation when behavior changes.
- Link related issues.

## Code of conduct expectations

Be respectful. This is a professional engineering project aimed at real operators.
