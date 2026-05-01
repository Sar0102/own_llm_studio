# Python Style Rules

## Python Version

Use modern Python syntax supported by the project.

Prefer:

```python
list[str]
dict[str, Any]
str | None
```

over old typing aliases unless the project requires compatibility.

## Type Annotations

All public functions, methods and class attributes must have type annotations.

Example:

```python
async def get_user_by_id(self, user_id: UUID) -> UserDTO | None:
    ...
```

## Docstrings

All public functions and methods must have docstrings.

Use concise docstrings that explain intent, not obvious implementation details.

Example:

```python
async def get_by_id(self, user_id: UUID) -> UserModel | None:
    """Return user by identifier or None if the user does not exist."""
```

## Function Design

Prefer small functions.

Each function should do one thing.

Avoid deeply nested logic.

Prefer early returns when they improve readability.

## Naming

Use intention-revealing names.

Good:

```python
calculate_total_amount()
get_active_users()
is_account_locked()
```

Bad:

```python
process()
handle()
data()
result()
```

Generic names are allowed only in very small local scopes.

## Imports

Group imports as:

1. standard library
2. third-party libraries
3. project imports

Avoid unused imports.

## Exceptions

Do not catch broad exceptions unless there is a clear reason.

Bad:

```python
try:
    ...
except Exception:
    pass
```

Good:

```python
try:
    ...
except IntegrityError as error:
    raise UserAlreadyExistsError() from error
```

## Async Code

Use async/await consistently.

Do not block the event loop with synchronous IO.

Avoid sync database sessions in async application code.

## Clean Code

Avoid:

- magic numbers
- hidden side effects
- long parameter lists
- boolean flags that change behavior drastically
- duplicated query logic
- mixing validation, persistence and business logic in one function
