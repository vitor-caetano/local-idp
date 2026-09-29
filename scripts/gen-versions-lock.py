#!/usr/bin/env python3
# ABOUTME: Regenerates the component table in versions.lock.md from components.yaml.
# ABOUTME: components.yaml is the source of truth; this keeps the human lookup honest.
"""Regenerate the component table in versions.lock.md from components.yaml.

Only the component table is generated. The prose above and below it is written by hand.

Usage:
    python3 scripts/gen-versions-lock.py            # rewrite versions.lock.md in place
    python3 scripts/gen-versions-lock.py --check    # exit 1 if the file is stale
"""
import argparse
import os
import sys

import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPONENTS = os.path.join(REPO_ROOT, "components.yaml")
LOCK = os.path.join(REPO_ROOT, "versions.lock.md")

HEADER = "| Component | App version | Chart | Chart version | Chart repo |"
SEPARATOR = "|---|---|---|---|---|"


def _chart_cells(component):
    """Return (chart, chart_version, chart_repo) as the table prints them."""
    if component.get("chart_name"):
        repo = str(component.get("chart_repo") or "n/a")
        for prefix in ("https://", "http://"):
            if repo.startswith(prefix):
                repo = repo[len(prefix):]
        return component["chart_name"], str(component.get("chart_version") or "n/a"), repo
    method = component.get("install_method", "n/a")
    return f"n/a ({method})", "n/a", "n/a"


def render_rows():
    with open(COMPONENTS) as handle:
        data = yaml.safe_load(handle)
    rows = []
    for component in data["components"]:
        name = component.get("display_name") or component["name"]
        chart, chart_version, repo = _chart_cells(component)
        rows.append(f"| {name} | {component['app_version']} | {chart} | {chart_version} | {repo} |")
    return rows


def render_lock():
    """Return the full lock file with only the component table replaced."""
    with open(LOCK) as handle:
        lines = handle.read().splitlines()
    try:
        start = lines.index(HEADER)
    except ValueError:
        raise SystemExit(f"{LOCK}: could not find the component table header:\n  {HEADER}")
    end = start + 2
    while end < len(lines) and lines[end].startswith("|"):
        end += 1
    return "\n".join(lines[:start] + [HEADER, SEPARATOR] + render_rows() + lines[end:]) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit 1 if the file is stale")
    args = parser.parse_args()

    rendered = render_lock()
    with open(LOCK) as handle:
        current = handle.read()

    if args.check:
        if rendered != current:
            print("versions.lock.md is stale. Run: python3 scripts/gen-versions-lock.py")
            return 1
        print("versions.lock.md matches components.yaml")
        return 0

    if rendered == current:
        print("versions.lock.md already matches components.yaml")
        return 0
    with open(LOCK, "w") as handle:
        handle.write(rendered)
    print("versions.lock.md regenerated from components.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
