# FastAPI API Rules

## Routers

Routers should be thin.

Routers may:

- parse HTTP input
- call application use cases/services
- return response DTOs
- map errors to HTTP responses

Routers must not contain business logic.

## DTOs

Use Pydantic v2.

Use separate schemas when responsibilities differ:

- request schema
- response schema
- internal application DTO

Avoid exposing SQLAlchemy models directly.

## Dependencies

Use FastAPI dependencies for:

- current user
- authorization
- Unit of Work
- application services
- settings
- request-scoped infrastructure

Do not hide complex business logic inside dependencies.

## HTTP Errors

Map domain/application errors to HTTP exceptions at the API boundary.

Example:

```python
try:
    result = await use_case.execute(command)
except UserNotFoundError as error:
    raise HTTPException(status_code=404, detail=str(error)) from error
```

Prefer centralized exception handlers for repeated errors.

## Status Codes

Use correct HTTP status codes:

- 200 for successful read/update
- 201 for created resources
- 204 for successful delete without response body
- 400 for invalid business request
- 401 for unauthenticated request
- 403 for authenticated but forbidden request
- 404 for missing resource
- 409 for conflict
- 422 for validation errors

## Pagination

For list endpoints, use pagination by default when data can grow.

Prefer limit/offset or cursor pagination depending on the use case.

For large frequently changing datasets, prefer cursor pagination.

## Validation

Pydantic validation should handle input shape and simple field constraints.

Business validation should live in domain/application layer.

## Security

Do not trust user input.

Do not expose internal error details.

Do not leak stack traces in API responses.

Do not return sensitive fields such as:

- password hashes
- tokens
- secrets
- internal security flags
