from __future__ import annotations

import math
import re
from typing import Any

from .contracts import ContractError


def validate_structure(value: Any, schema: dict, location: str = "$", *, root_schema: dict | None = None) -> None:
    """Validate the JSON Schema keywords used by obscript's versioned schemas."""
    root_schema = schema if root_schema is None else root_schema
    if "$ref" in schema:
        reference = schema["$ref"]
        if not reference.startswith("#/"):
            raise ContractError(f"Unsupported schema reference: {reference}")
        schema = root_schema
        for part in reference[2:].split("/"):
            schema = schema[part.replace("~1", "/").replace("~0", "~")]

    kind = schema.get("type")
    valid = {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }
    if kind not in valid or not valid[kind]:
        raise ContractError(f"{location}: expected {kind}")
    if "const" in schema and value != schema["const"]:
        raise ContractError(f"{location}: expected {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        raise ContractError(f"{location}: expected one of {schema['enum']!r}")
    if kind == "object":
        properties = schema.get("properties", {})
        missing = set(schema.get("required", [])) - value.keys()
        extra = value.keys() - properties.keys() if schema.get("additionalProperties") is False else set()
        if missing or extra:
            raise ContractError(f"{location}: missing {sorted(missing)}, unknown {sorted(extra)}")
        for key, child in value.items():
            if key in properties:
                validate_structure(child, properties[key], f"{location}.{key}", root_schema=root_schema)
    elif kind == "array":
        if len(value) < schema.get("minItems", 0):
            raise ContractError(f"{location}: too few items")
        for index, child in enumerate(value):
            validate_structure(child, schema["items"], f"{location}[{index}]", root_schema=root_schema)
    elif kind == "string":
        if len(value.strip()) < schema.get("minLength", 0):
            raise ContractError(f"{location}: empty text")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            raise ContractError(f"{location}: invalid identifier")
    elif kind in {"number", "integer"}:
        if not math.isfinite(value):
            raise ContractError(f"{location}: duration must be finite")
        if "minimum" in schema and value < schema["minimum"]:
            raise ContractError(f"{location}: below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            raise ContractError(f"{location}: above maximum")
        if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
            raise ContractError(f"{location}: must exceed minimum")

