import json
from functools import lru_cache
from pathlib import Path
from typing import Any


class SandboxTopologyValidationError(ValueError):
    pass


@lru_cache(maxsize=1)
def _schema() -> dict[str, Any]:
    schema_path = _schema_path()
    return json.loads(schema_path.read_text(encoding="utf-8"))


def _schema_path() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "sandbox-topology.schema.json"
        if candidate.exists():
            return candidate
    raise SandboxTopologyValidationError("sandbox topology schema file not found")


def validate_sandbox_topology_request(sandbox_request: dict[str, Any]) -> None:
    topology = _extract_topology(sandbox_request)
    if topology is None:
        return
    validate_sandbox_topology(topology)


def validate_sandbox_topology(topology: dict[str, Any]) -> None:
    error = _validate_value(topology, _schema(), _schema(), [])
    if error:
        raise SandboxTopologyValidationError("Invalid sandbox topology: " + error)


def _extract_topology(sandbox_request: dict[str, Any]) -> dict[str, Any] | None:
    topology = sandbox_request.get("topology")
    if isinstance(topology, dict):
        return topology
    if topology is not None:
        raise SandboxTopologyValidationError("Invalid sandbox topology: topology must be an object")

    topology_json = sandbox_request.get("topology_json")
    if not topology_json:
        return None
    if not isinstance(topology_json, str):
        raise SandboxTopologyValidationError(
            "Invalid sandbox topology: topology_json must be a JSON string"
        )
    try:
        parsed = json.loads(topology_json)
    except json.JSONDecodeError as exc:
        raise SandboxTopologyValidationError(
            f"Invalid sandbox topology JSON: {exc.msg} at line {exc.lineno} column {exc.colno}"
        ) from exc
    if not isinstance(parsed, dict):
        raise SandboxTopologyValidationError("Invalid sandbox topology: root must be an object")
    return parsed


def _validate_value(
    value: Any, schema: dict[str, Any], root_schema: dict[str, Any], path: list[Any]
) -> str | None:
    if "$ref" in schema:
        schema = _resolve_ref(root_schema, schema["$ref"])

    expected_type = schema.get("type")
    if expected_type and not _matches_type(value, expected_type):
        return f"{_format_path(path)}: expected {expected_type}, got {_type_name(value)}"

    if expected_type == "object":
        if not isinstance(value, dict):
            return f"{_format_path(path)}: expected object, got {_type_name(value)}"
        for required in schema.get("required", []):
            if required not in value:
                return f"{_format_path(path)}: missing required property '{required}'"
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for key, item in value.items():
            if key in properties:
                error = _validate_value(item, properties[key], root_schema, path + [key])
            elif isinstance(additional, dict):
                error = _validate_value(item, additional, root_schema, path + [key])
            elif additional is False:
                error = f"{_format_path(path + [key])}: unexpected property"
            else:
                error = None
            if error:
                return error

    if expected_type == "array":
        if not isinstance(value, list):
            return f"{_format_path(path)}: expected array, got {_type_name(value)}"
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(value):
                error = _validate_value(item, item_schema, root_schema, path + [index])
                if error:
                    return error

    if expected_type == "string":
        min_length = schema.get("minLength")
        if isinstance(min_length, int) and len(value) < min_length:
            return f"{_format_path(path)}: string length must be >= {min_length}"

    if expected_type == "integer":
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if isinstance(minimum, int) and value < minimum:
            return f"{_format_path(path)}: integer must be >= {minimum}"
        if isinstance(maximum, int) and value > maximum:
            return f"{_format_path(path)}: integer must be <= {maximum}"

    return None


def _resolve_ref(root_schema: dict[str, Any], ref: str) -> dict[str, Any]:
    if not ref.startswith("#/"):
        raise SandboxTopologyValidationError(f"unsupported schema ref {ref}")
    current: Any = root_schema
    for part in ref[2:].split("/"):
        current = current[part]
    return current


def _matches_type(value: Any, expected_type: str) -> bool:
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    return True


def _type_name(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    if isinstance(value, int):
        return "integer"
    return type(value).__name__


def _format_path(path: list[Any]) -> str:
    return ".".join(str(part) for part in path) if path else "root"
