# Database and SQLAlchemy Rules

## SQLAlchemy Version

Use SQLAlchemy 2.x style.

Prefer:

```python
from sqlalchemy.orm import Mapped, mapped_column
```

Example:

```python
class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(32), unique=True, index=True)
```

## Async SQLAlchemy

Use async SQLAlchemy with AsyncSession.

Repository methods that access the database must be async.

Example:

```python
class UsersRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: UUID) -> UserModel | None:
        """Return user by identifier."""
        stmt = select(UserModel).where(UserModel.id == user_id)
        return await self._session.scalar(stmt)
```

## Repository Pattern

All persistence logic must be inside repositories.

Do not write SQLAlchemy queries directly in FastAPI routers.

Do not commit inside repositories.

Repositories may call:

```python
self._session.add()
self._session.flush()
self._session.scalar()
self._session.scalars()
self._session.execute()
```

Commit/rollback should be handled by Unit of Work.

## Query Optimization

Prefer database-side filtering, sorting and aggregation.

Avoid loading large datasets into Python for filtering.

Good:

```python
select(func.count()).select_from(UserModel).where(UserModel.is_active.is_(True))
```

Bad:

```python
users = await repo.get_all()
active_count = len([user for user in users if user.is_active])
```

## Loading Strategy

Use:

- `selectinload` for collections
- `joinedload` for one-to-one or many-to-one when it does not multiply rows too much
- explicit joins for filtering and aggregation

Avoid N+1 queries.

## Transactions

Use one transaction per use case unless there is a strong reason.

Do not commit after every repository call.

## Alembic

Every schema change must have an Alembic migration.

Migration should include:

- table creation
- index creation
- enum creation/update if needed
- nullable changes
- constraints
- downgrade where possible

## PostgreSQL

Use PostgreSQL features carefully:

- JSONB for flexible structured data
- indexes for frequent filters
- GIN indexes for JSONB/search when needed
- partial indexes for filtered queries when useful
- constraints for data integrity

Do not use JSONB as a replacement for relational modeling when fields are stable and frequently queried.

## Performance

For queries, consider:

- number of rows scanned
- index usage
- N+1 risk
- memory usage
- unnecessary joins
- unnecessary eager loading

When possible, explain complexity:

- DB filtering: usually O(log n) with index, O(n) without index
- Python filtering after loading rows: O(n) memory and O(n) CPU
