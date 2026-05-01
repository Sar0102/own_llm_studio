# Testing Rules

## General

Write tests for behavior, not implementation details.

Prefer small, focused tests.

Use clear test names.

## Test Structure

Use Arrange / Act / Assert.

Example:

```python
async def test_user_can_be_created() -> None:
    """User is persisted when valid data is provided."""
    # Arrange

    # Act

    # Assert
```

## What to Test

Prioritize tests for:

- domain invariants
- use cases
- repository behavior
- API contracts
- error handling
- transaction behavior
- permissions

## Async Tests

Use async tests for async code.

Do not call async functions without awaiting them.

## Database Tests

Database tests should verify:

- persistence
- constraints
- relationships
- repository methods
- transaction rollback/commit behavior

## Mocking

Mock external systems:

- SMS providers
- email providers
- payment providers
- external APIs
- message brokers when integration is not the goal

Do not mock the code under test.

## Verification

After changes, run the smallest relevant test scope.

Examples:

```bash
pytest tests/unit/domain/test_user.py
pytest tests/integration/repositories/test_users_repository.py
pytest tests/api/test_users.py
```

If tests cannot be run, explain the recommended verification command.
