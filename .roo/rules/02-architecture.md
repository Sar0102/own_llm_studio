# Architecture Rules

## Layers

Use Clean Architecture boundaries:

```text
src/
  domain/
    entities/
    value_objects/
    services/
    events/
    exceptions/

  application/
    use_cases/
    services/
    dto/
    interfaces/

  infrastructure/
    database/
      models/
      repositories/
      mappings/
    external_services/

  presentation/
    api/
      routers/
      dependencies/
      schemas/
```

## Dependency Direction

Dependencies must point inward:

```text
presentation -> application -> domain
infrastructure -> application/domain interfaces
domain -> no external dependencies
```

The domain layer must not depend on:

- FastAPI
- SQLAlchemy
- Pydantic
- Redis
- Kafka
- RabbitMQ
- HTTP clients
- external SDKs

## Domain Layer

Domain layer should contain:

- entities
- value objects
- domain services
- domain events
- domain exceptions
- business invariants

Domain entities should protect invariants through methods.

Avoid anemic domain models when there is meaningful business behavior.

## Application Layer

Application layer should contain:

- use cases
- command/query handlers
- application services
- interfaces for repositories and external services
- transaction boundaries through Unit of Work

Application layer coordinates business flow but should not contain infrastructure details.

## Infrastructure Layer

Infrastructure layer should contain:

- SQLAlchemy models
- repository implementations
- Unit of Work implementation
- external API clients
- message broker adapters
- cache adapters

Infrastructure must implement interfaces defined by application/domain layers.

## Presentation Layer

Presentation layer should contain:

- FastAPI routers
- dependencies
- request/response schemas
- HTTP error mapping
- authentication/authorization dependencies

Do not put business logic in routers.

## Repository Pattern

Repositories should:

- hide persistence details
- work with domain entities or application DTOs depending on project style
- expose intention-revealing methods
- avoid leaking raw SQLAlchemy queries outside infrastructure unless explicitly required

Example method names:

```python
get_by_id()
get_by_phone()
create()
update()
delete()
exists_by_email()
```

## Unit of Work

Use Unit of Work for transactional use cases.

A use case should commit only once, at the application boundary.

Avoid committing inside repositories.

## CQRS

Use CQRS when read and write models differ significantly.

Use commands for mutations.
Use queries for reads.

Do not introduce CQRS for simple CRUD unless it improves clarity.

## Domain Errors

Raise domain/application exceptions inside domain/application layers.

Map these exceptions to HTTP responses only in the presentation layer.
