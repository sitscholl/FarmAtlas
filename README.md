## Schema Flow

Frontend API types are generated from the FastAPI OpenAPI schema.

- `npm run dev`, `npm run build`, and `npm run lint` in [`frontend/package.json`](c:/Users/tscho/Documents/_Coding/FarmAtlas/frontend/package.json) automatically run `npm run generate:types` first.
- You can also regenerate manually with `npm run generate:types` inside [`frontend`](c:/Users/tscho/Documents/_Coding/FarmAtlas/frontend).

## Add A New Model

1. Add the SQLAlchemy table/model in [backend/src/database/models.py](c:/Users/tscho/Documents/_Coding/FarmAtlas/backend/src/database/models.py).
2. Add or extend the database access methods in [backend/src/database/db.py](c:/Users/tscho/Documents/_Coding/FarmAtlas/backend/src/database/db.py).
3. Add the API schemas in [backend/src/schemas](c:/Users/tscho/Documents/_Coding/FarmAtlas/backend/src/schemas).
4. Add or update the FastAPI endpoints in [backend/src/api.py](c:/Users/tscho/Documents/_Coding/FarmAtlas/backend/src/api.py) using those schemas as request and response models.
5. Run `npm run generate:types` in [`frontend`](c:/Users/tscho/Documents/_Coding/FarmAtlas/frontend), or just start the frontend and let `predev` do it automatically.
6. Use the generated types from [frontend/src/types/generated/api.ts](c:/Users/tscho/Documents/_Coding/FarmAtlas/frontend/src/types/generated/api.ts) in the React code. Do not create handwritten duplicate API types.

## Rule Of Thumb

- Database structure lives in SQLAlchemy models.
- API contract lives in backend Pydantic schemas.
- Frontend contract lives only in generated types.
