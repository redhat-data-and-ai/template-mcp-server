"""Tests for JSON Schema 2020-12 validation utilities (SEP-2106)."""

import pytest

from template_mcp_server.src.schema import (
    ALLOWED_2020_12_KEYWORDS,
    COMPOSITION_KEYWORDS,
    JSON_SCHEMA_2020_12_URI,
    REFERENCE_KEYWORDS,
    _collect_refs,
    _validate_refs,
    ensure_schema_2020_12,
    validate_input_schema,
    validate_output_schema,
)


class TestValidateInputSchema:
    """Validate inputSchema compliance with JSON Schema 2020-12."""

    def test_valid_object_root(self):
        schema = {
            "type": "object",
            "properties": {"x": {"type": "string"}},
            "required": ["x"],
        }
        assert validate_input_schema(schema) == []

    def test_rejects_non_object_root_type(self):
        schema = {"type": "array", "items": {"type": "string"}}
        errors = validate_input_schema(schema)
        assert any('type: "object"' in e for e in errors)

    def test_rejects_missing_type(self):
        schema = {"properties": {"x": {"type": "string"}}}
        errors = validate_input_schema(schema)
        assert any('type: "object"' in e for e in errors)

    def test_rejects_non_dict(self):
        errors = validate_input_schema("not a dict")
        assert errors == ["inputSchema must be a JSON object"]

    def test_valid_with_composition_keywords(self):
        schema = {
            "type": "object",
            "properties": {
                "value": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "integer"},
                    ]
                }
            },
        }
        assert validate_input_schema(schema) == []

    def test_valid_with_anyOf(self):
        schema = {
            "type": "object",
            "properties": {
                "data": {
                    "anyOf": [
                        {"type": "string"},
                        {"type": "object", "properties": {"key": {"type": "string"}}},
                    ]
                }
            },
        }
        assert validate_input_schema(schema) == []

    def test_valid_with_allOf(self):
        schema = {
            "type": "object",
            "allOf": [
                {"properties": {"a": {"type": "string"}}},
                {"properties": {"b": {"type": "integer"}}},
            ],
        }
        assert validate_input_schema(schema) == []

    def test_valid_with_defs_and_ref(self):
        schema = {
            "type": "object",
            "properties": {"measurement": {"$ref": "#/$defs/Measurement"}},
            "$defs": {
                "Measurement": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "number"},
                        "unit": {"type": "string"},
                    },
                }
            },
        }
        assert validate_input_schema(schema) == []

    def test_rejects_unresolved_ref(self):
        schema = {
            "type": "object",
            "properties": {"data": {"$ref": "#/$defs/Missing"}},
        }
        errors = validate_input_schema(schema)
        assert any("does not resolve" in e for e in errors)

    def test_valid_schema_uri(self):
        schema = {
            "$schema": JSON_SCHEMA_2020_12_URI,
            "type": "object",
            "properties": {},
        }
        assert validate_input_schema(schema) == []

    def test_rejects_wrong_schema_uri(self):
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {},
        }
        errors = validate_input_schema(schema)
        assert any("$schema must be" in e for e in errors)

    def test_valid_with_nested_refs(self):
        schema = {
            "type": "object",
            "properties": {
                "a": {"$ref": "#/$defs/A"},
            },
            "$defs": {
                "A": {
                    "type": "object",
                    "properties": {
                        "b": {"$ref": "#/$defs/B"},
                    },
                },
                "B": {"type": "string"},
            },
        }
        assert validate_input_schema(schema) == []


class TestValidateOutputSchema:
    """Validate outputSchema compliance with JSON Schema 2020-12."""

    def test_none_is_valid(self):
        assert validate_output_schema(None) == []

    def test_object_type_is_valid(self):
        schema = {
            "type": "object",
            "properties": {"result": {"type": "string"}},
        }
        assert validate_output_schema(schema) == []

    def test_any_root_type_is_valid(self):
        for root_type in ["string", "number", "integer", "boolean", "array", "null"]:
            schema = {"type": root_type}
            assert validate_output_schema(schema) == [], f"Failed for type: {root_type}"

    def test_rejects_non_dict(self):
        errors = validate_output_schema("not a dict")
        assert errors == ["outputSchema must be a JSON object"]

    def test_rejects_wrong_schema_uri(self):
        schema = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "type": "object",
        }
        errors = validate_output_schema(schema)
        assert any("$schema must be" in e for e in errors)

    def test_validates_refs_in_output_schema(self):
        schema = {
            "type": "object",
            "properties": {"data": {"$ref": "#/$defs/Missing"}},
        }
        errors = validate_output_schema(schema)
        assert any("does not resolve" in e for e in errors)


class TestValidateRefs:
    """Test $ref resolution within $defs."""

    def test_valid_ref(self):
        schema = {
            "$defs": {"Foo": {"type": "string"}},
            "properties": {"x": {"$ref": "#/$defs/Foo"}},
        }
        assert _validate_refs(schema) == []

    def test_unresolved_ref(self):
        schema = {
            "properties": {"x": {"$ref": "#/$defs/Bar"}},
        }
        errors = _validate_refs(schema)
        assert len(errors) == 1
        assert "Bar" in errors[0]

    def test_external_ref_ignored(self):
        schema = {
            "properties": {"x": {"$ref": "https://example.com/schema.json"}},
        }
        assert _validate_refs(schema) == []

    def test_multiple_unresolved_refs(self):
        schema = {
            "properties": {
                "a": {"$ref": "#/$defs/X"},
                "b": {"$ref": "#/$defs/Y"},
            },
        }
        errors = _validate_refs(schema)
        assert len(errors) == 2


class TestCollectRefs:
    """Test recursive $ref collection from schema trees."""

    def test_no_refs(self):
        assert _collect_refs({"type": "object"}) == []

    def test_single_ref(self):
        assert _collect_refs({"$ref": "#/$defs/Foo"}) == ["#/$defs/Foo"]

    def test_nested_refs(self):
        schema = {
            "properties": {
                "a": {"$ref": "#/$defs/A"},
                "b": {
                    "type": "object",
                    "properties": {
                        "c": {"$ref": "#/$defs/C"},
                    },
                },
            },
        }
        refs = _collect_refs(schema)
        assert set(refs) == {"#/$defs/A", "#/$defs/C"}

    def test_refs_in_arrays(self):
        schema = {
            "oneOf": [
                {"$ref": "#/$defs/A"},
                {"$ref": "#/$defs/B"},
            ]
        }
        refs = _collect_refs(schema)
        assert set(refs) == {"#/$defs/A", "#/$defs/B"}

    def test_non_dict_input(self):
        assert _collect_refs("string") == []
        assert _collect_refs(42) == []
        assert _collect_refs(None) == []


class TestEnsureSchema2020_12:
    """Test $schema injection."""

    def test_adds_schema_when_missing(self):
        schema = {"type": "object", "properties": {}}
        result = ensure_schema_2020_12(schema)
        assert result["$schema"] == JSON_SCHEMA_2020_12_URI
        assert result["type"] == "object"

    def test_preserves_existing_schema(self):
        uri = "https://custom-schema.example.com"
        schema = {"$schema": uri, "type": "object"}
        result = ensure_schema_2020_12(schema)
        assert result["$schema"] == uri

    def test_does_not_mutate_original(self):
        schema = {"type": "object"}
        result = ensure_schema_2020_12(schema)
        assert "$schema" not in schema
        assert "$schema" in result


class TestSchemaConstants:
    """Test that schema constants are correctly defined."""

    def test_composition_keywords(self):
        assert "oneOf" in COMPOSITION_KEYWORDS
        assert "anyOf" in COMPOSITION_KEYWORDS
        assert "allOf" in COMPOSITION_KEYWORDS

    def test_reference_keywords(self):
        assert "$ref" in REFERENCE_KEYWORDS
        assert "$defs" in REFERENCE_KEYWORDS

    def test_composition_and_reference_in_allowed(self):
        assert COMPOSITION_KEYWORDS.issubset(ALLOWED_2020_12_KEYWORDS)
        assert REFERENCE_KEYWORDS.issubset(ALLOWED_2020_12_KEYWORDS)

    def test_json_schema_uri(self):
        assert "2020-12" in JSON_SCHEMA_2020_12_URI
