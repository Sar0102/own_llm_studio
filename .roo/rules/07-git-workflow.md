# Git Workflow Rules

## Change Scope

Keep changes focused.

Do not mix unrelated refactoring with feature work unless explicitly requested.

## Before Editing

Before editing files:

1. Inspect existing implementation.
2. Check naming conventions.
3. Check nearby tests.
4. Check existing error handling.
5. Check existing DTO/repository/service patterns.

## After Editing

After editing:

1. Summarize changed files.
2. Explain why changes were needed.
3. Mention how to verify.
4. Mention risks or trade-offs.

## Commit Messages

When asked to create commit messages, use this format:

```text
type(scope): short description
```

Types:

- feat
- fix
- refactor
- test
- docs
- chore
- perf

Examples:

```text
feat(auth): add OTP verification use case
fix(users): handle duplicate phone validation
refactor(db): extract base repository
```
