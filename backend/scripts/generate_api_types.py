from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_TYPES_DIR = ROOT_DIR / "frontend" / "src" / "types" / "generated"
FRONTEND_TYPES_FILE = FRONTEND_TYPES_DIR / "api.ts"


def _quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=True)


def _ref_name(schema: dict[str, Any]) -> str:
    ref = schema["$ref"]
    return ref.rsplit("/", 1)[-1]


def _schema_to_ts(schema: dict[str, Any]) -> str:
    if "$ref" in schema:
        return _ref_name(schema)

    if "enum" in schema:
        return " | ".join(_quote(str(option)) for option in schema["enum"])

    if "anyOf" in schema:
        return " | ".join(_schema_to_ts(option) for option in schema["anyOf"])

    if "oneOf" in schema:
        return " | ".join(_schema_to_ts(option) for option in schema["oneOf"])

    if "allOf" in schema:
        return " & ".join(_schema_to_ts(option) for option in schema["allOf"])

    schema_type = schema.get("type")

    if schema_type == "array":
        return f"Array<{_schema_to_ts(schema['items'])}>"

    if schema_type == "object" or "properties" in schema:
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))
        additional_properties = schema.get("additionalProperties")

        lines: list[str] = ["{"]
        for property_name, property_schema in properties.items():
            optional = "?" if property_name not in required else ""
            lines.append(
                f"  {property_name}{optional}: {_schema_to_ts(property_schema)}"
            )

        if additional_properties:
            lines.append(
                f"  [key: string]: {_schema_to_ts(additional_properties)}"
            )

        lines.append("}")
        return "\n".join(lines)

    if schema_type in {"integer", "number"}:
        return "number"

    if schema_type == "string":
        return "string"

    if schema_type == "boolean":
        return "boolean"

    if schema_type == "null":
        return "null"

    return "unknown"


def _render_schema_alias(name: str, schema: dict[str, Any]) -> str:
    return f"export type {name} = {_schema_to_ts(schema)}\n"


def main() -> None:
    os.chdir(BACKEND_DIR)
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))

    from src.api import app

    openapi_schema = app.openapi()
    component_schemas = openapi_schema.get("components", {}).get("schemas", {})

    FRONTEND_TYPES_DIR.mkdir(parents=True, exist_ok=True)

    content_parts = [
        "/*",
        " * This file is auto-generated from the FastAPI OpenAPI schema.",
        " * Do not edit it manually. Run `npm run generate:types` in the frontend directory instead.",
        " */",
        "",
    ]

    for schema_name in sorted(component_schemas):
        content_parts.append(_render_schema_alias(schema_name, component_schemas[schema_name]).rstrip())
        content_parts.append("")

    FRONTEND_TYPES_FILE.write_text("\n".join(content_parts).rstrip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
