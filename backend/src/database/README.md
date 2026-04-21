## Database Package

This package is split into three layers:

- `models.py`: SQLAlchemy table definitions.
- `repositories/`: persistence-only data access. Repositories read and write database rows but should not contain cross-entity business rules.
- `services/`: write-side orchestration and side effects. Services are only needed when an operation touches multiple repositories or applies business rules.

Supporting files:

- `core.py`: engine and session management.
- `db.py`: composition root that wires repositories and services into one `Database` object.
- `settings.py`: resolves the effective database URL from config or `DATABASE_URL`.
- `../../alembic/`: schema migration history and Alembic environment.

## Current Rule Of Thumb

- Use repositories directly for reads.
- Use repositories directly for simple writes that only affect one table.
- Use services for writes that need side effects, validation across entities, or cache invalidation.
- Use Alembic migrations for every schema change. `create_all()` is now opt-in and only intended for disposable test databases.

## Add A New Table

1. Add the SQLAlchemy model in [`models.py`](c:/Users/tscho/Documents/_Coding/FarmAtlas/backend/src/database/models.py).
2. Create an Alembic migration from [`backend`](c:/Users/tscho/Documents/_Coding/FarmAtlas/backend) with `alembic revision --autogenerate -m "add <table>"`.
3. Review the generated migration and then apply it with `alembic upgrade head`.
4. If the table needs direct persistence access, add a repository in [`repositories/`](c:/Users/tscho/Documents/_Coding/FarmAtlas/backend/src/database/repositories).
5. Export the repository in [`repositories/__init__.py`](c:/Users/tscho/Documents/_Coding/FarmAtlas/backend/src/database/repositories/__init__.py).
6. Wire the repository in [`db.py`](c:/Users/tscho/Documents/_Coding/FarmAtlas/backend/src/database/db.py) as `db.<name>`.
7. If writes to the new table need cross-table rules or side effects, add a service in [`services/`](c:/Users/tscho/Documents/_Coding/FarmAtlas/backend/src/database/services).
8. Export the service in [`services/__init__.py`](c:/Users/tscho/Documents/_Coding/FarmAtlas/backend/src/database/services/__init__.py).
9. Wire the service in [`db.py`](c:/Users/tscho/Documents/_Coding/FarmAtlas/backend/src/database/db.py) as `db.<name>_service`.
10. Update callers to use:
   - `with db.session_scope() as session: db.<repository>.<method>(session, ...)` for repository access
   - `db.<service>.<method>(...)` for business operations

## Add New Methods

1. If the method only queries or persists one entity, add it to the repository.
2. If the method coordinates multiple repositories or performs side effects, add it to a service.
3. Keep transaction boundaries explicit:
   - repositories accept a `session`
   - services own their own `session_scope()` unless there is a strong reason not to
4. Keep repositories free of workflow logic, cache invalidation, and UI/API concerns.
