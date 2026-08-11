"""JSON Schema 2020-12 validation utilities per SEP-2106.

Validates tool input/output schemas for compliance with JSON Schema 2020-12,
ensuring inputSchema roots are type: "object" and that composition keywords
(oneOf, anyOf, allOf, $ref, $defs) are well-formed.
"""

from typing import Any, Dict, List, Optional

JSON_SCHEMA_2020_12_URI = "https://json-schema.org/draft/2020-12/schema"

COMPOSITION_KEYWORDS = frozenset({"oneOf", "anyOf", "allOf"})

REFERENCE_KEYWORDS = frozenset({"$ref", "$defs"})

ALLOWED_2020_12_KEYWORDS = frozenset(
    {
        "type",
        "properties",
        "required",
        "additionalProperties",
        "items",
        "enum",
        "const",
        "default",
        "description",
        "title",
        "examples",
        "format",
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "minLength",
        "maxLength",
        "pattern",
        "minItems",
        "maxItems",
        "uniqueItems",
        "minProperties",
        "maxProperties",
        "multipleOf",
        "not",
        "if",
        "then",
        "else",
        "dependentRequired",
        "dependentSchemas",
        "prefixItems",
        "contains",
        "minContains",
        "maxContains",
        "patternProperties",
        "propertyNames",
        "unevaluatedItems",
        "unevaluatedProperties",
        "$schema",
        "$id",
        "$anchor",
        "$comment",
        "$dynamicAnchor",
        "$dynamicRef",
        "$vocabulary",
        "contentEncoding",
        "contentMediaType",
        "contentSchema",
        "deprecated",
        "readOnly",
        "writeOnly",
    }
    | COMPOSITION_KEYWORDS
    | REFERENCE_KEYWORDS
)


def validate_input_schema(schema: Any) -> List[str]:
    """Validate a tool inputSchema for JSON Schema 2020-12 compliance.

    Returns a list of error strings. Empty list means valid.
    """
    errors: List[str] = []

    if not isinstance(schema, dict):
        errors.append("inputSchema must be a JSON object")
        return errors

    root_type = schema.get("type")
    if root_type != "object":
        errors.append(f'inputSchema root must have type: "object", got: {root_type!r}')

    if "$schema" in schema:
        schema_uri = schema["$schema"]
        if schema_uri != JSON_SCHEMA_2020_12_URI:
            errors.append(
                f"$schema must be {JSON_SCHEMA_2020_12_URI}, got: {schema_uri!r}"
            )

    ref_errors = _validate_refs(schema)
    errors.extend(ref_errors)

    return errors


def validate_output_schema(schema: Any) -> List[str]:
    """Validate a tool outputSchema for JSON Schema 2020-12 compliance.

    Output schemas may have any root type per SEP-2106.
    Returns a list of error strings. Empty list means valid.
    """
    if schema is None:
        return []

    errors: List[str] = []

    if not isinstance(schema, dict):
        errors.append("outputSchema must be a JSON object")
        return errors

    if "$schema" in schema:
        schema_uri = schema["$schema"]
        if schema_uri != JSON_SCHEMA_2020_12_URI:
            errors.append(
                f"$schema must be {JSON_SCHEMA_2020_12_URI}, got: {schema_uri!r}"
            )

    ref_errors = _validate_refs(schema)
    errors.extend(ref_errors)

    return errors


def _validate_refs(schema: Dict[str, Any]) -> List[str]:
    """Validate that all $ref references resolve within $defs."""
    errors: List[str] = []
    defs = schema.get("$defs", {})
    refs = _collect_refs(schema)

    for ref in refs:
        if ref.startswith("#/$defs/"):
            def_name = ref[len("#/$defs/") :]
            if def_name not in defs:
                errors.append(
                    f"$ref {ref!r} does not resolve: {def_name!r} not in $defs"
                )

    return errors


def _collect_refs(node: Any, refs: Optional[List[str]] = None) -> List[str]:
    """Recursively collect all $ref values from a schema tree."""
    if refs is None:
        refs = []

    if isinstance(node, dict):
        if "$ref" in node:
            refs.append(node["$ref"])
        for value in node.values():
            _collect_refs(value, refs)
    elif isinstance(node, list):
        for item in node:
            _collect_refs(item, refs)

    return refs


def ensure_schema_2020_12(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of the schema with $schema set to 2020-12 if not already present."""
    if "$schema" in schema:
        return schema
    return {"$schema": JSON_SCHEMA_2020_12_URI, **schema}
