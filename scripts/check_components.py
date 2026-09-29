#!/usr/bin/env python3
# ABOUTME: Fails if any components.yaml entry lacks a pinned version.
# ABOUTME: No count assertion: the set is the right set, not a number.
"""Validate the component manifest.

Every component must have a non-empty app_version, plane and phase. Components installed via Helm
must also have a non-empty chart_version.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

HELM_METHODS = {"helm", "helm-oci"}
PLANES = {"cluster", "foundation", "self-service"}


def validate(data: dict) -> list[str]:
    """Return a list of human-readable errors, empty when the manifest is valid."""
    errors: list[str] = []
    components = data.get("components")
    if not components:
        return ["components.yaml has no components"]

    seen: set[str] = set()
    for index, component in enumerate(components):
        name = component.get("name") or f"<entry {index}>"
        if name in seen:
            errors.append(f"{name}: duplicate entry")
        seen.add(name)

        if not component.get("app_version"):
            errors.append(f"{name}: missing app_version")
        if component.get("plane") not in PLANES:
            errors.append(f"{name}: plane must be one of {sorted(PLANES)}")
        if component.get("phase") is None:
            errors.append(f"{name}: missing phase")
        if component.get("install_method") in HELM_METHODS and not component.get("chart_version"):
            errors.append(f"{name}: helm install without a pinned chart_version")

    return errors


def main(path: str = "components.yaml") -> int:
    manifest = Path(path)
    if not manifest.exists():
        print(f"error: {path} not found", file=sys.stderr)
        return 1

    data = yaml.safe_load(manifest.read_text())
    errors = validate(data)
    if errors:
        print("components.yaml failed validation:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"components.yaml is valid: {len(data['components'])} components, all pinned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:]))
