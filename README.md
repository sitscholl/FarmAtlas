## Schema Flow

Frontend API types are generated from the FastAPI OpenAPI schema.

- `npm run dev`, `npm run build`, and `npm run lint` in [`frontend/package.json`](c:/Users/tscho/Documents/_Coding/FarmAtlas/frontend/package.json) automatically run `npm run generate:types` first.
- You can also regenerate manually with `npm run generate:types` inside [`frontend`](c:/Users/tscho/Documents/_Coding/FarmAtlas/frontend).

## Add A New Model

1. Add the SQLAlchemy table/model in [backend/src/database/models.py](c:/Users/tscho/Documents/_Coding/FarmAtlas/backend/src/database/models.py).
2. Create an Alembic migration in [`backend`](c:/Users/tscho/Documents/_Coding/FarmAtlas/backend) with `alembic revision --autogenerate -m "describe change"` and review the generated file.
3. Apply it locally with `alembic upgrade head`.
4. Add or extend the database access methods in [backend/src/database/db.py](c:/Users/tscho/Documents/_Coding/FarmAtlas/backend/src/database/db.py).
5. Add the API schemas in [backend/src/schemas](c:/Users/tscho/Documents/_Coding/FarmAtlas/backend/src/schemas).
6. Add or update the FastAPI endpoints in [backend/src/api.py](c:/Users/tscho/Documents/_Coding/FarmAtlas/backend/src/api.py) using those schemas as request and response models.
7. Run `npm run generate:types` in [`frontend`](c:/Users/tscho/Documents/_Coding/FarmAtlas/frontend), or just start the frontend and let `predev` do it automatically.
8. Use the generated types from [frontend/src/types/generated/api.ts](c:/Users/tscho/Documents/_Coding/FarmAtlas/frontend/src/types/generated/api.ts) in the React code. Do not create handwritten duplicate API types.

## Rule Of Thumb

- Database structure lives in SQLAlchemy models.
- Database evolution lives in Alembic migrations under [`backend/alembic/versions`](c:/Users/tscho/Documents/_Coding/FarmAtlas/backend/alembic/versions).
- API contract lives in backend Pydantic schemas.
- Frontend contract lives only in generated types.

## Database Migrations

Run Alembic commands from [`backend`](c:/Users/tscho/Documents/_Coding/FarmAtlas/backend):

```bash
alembic upgrade head
alembic revision --autogenerate -m "add orchard table"
```

`--autogenerate` compares the current SQLAlchemy metadata to the live database schema. Review the generated migration before applying it, especially on SQLite where table rewrites are common.

For an existing production database that predates Alembic, do a one-time backup and baseline stamp before deploying a version that runs migrations automatically:

```bash
alembic stamp 0001_initial_schema
```
