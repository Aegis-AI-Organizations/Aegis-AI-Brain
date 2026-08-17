import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, ValidationError


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
    validator = Draft202012Validator(_schema())
    try:
        validator.validate(topology)
    except ValidationError as exc:
        path = _format_path(list(exc.absolute_path))
        location = f"{path}: " if path != "root" else ""
        raise SandboxTopologyValidationError(
            f"Invalid sandbox topology: {location}{exc.message}"
        ) from exc


def _extract_topology(sandbox_request: dict[str, Any]) -> dict[str, Any] | None:
    topology = sandbox_request.get("topology")
    if isinstance(topology, dict):
        return topology
    if topology is not None:
        raise SandboxTopologyValidationError(
            "Invalid sandbox topology: topology must be an object"
        )

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
        raise SandboxTopologyValidationError(
            "Invalid sandbox topology: root must be an object"
        )
    return parsed


def _format_path(path: list[Any]) -> str:
    return ".".join(str(part) for part in path) if path else "root"
