# ABOUTME: components.yaml is pinned and complete, and versions.lock.md agrees with it.
# ABOUTME: Cluster-free.
import importlib.util
import os
import subprocess
import sys

import pytest

yaml = pytest.importorskip("yaml")

from conftest import REPO_ROOT


def _load_checker():
    path = os.path.join(REPO_ROOT, "scripts", "check_components.py")
    spec = importlib.util.spec_from_file_location("check_components", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _components():
    with open(os.path.join(REPO_ROOT, "components.yaml")) as handle:
        return yaml.safe_load(handle)


def test_every_component_is_pinned():
    errors = _load_checker().validate(_components())
    assert not errors, "\n".join(errors)


def test_checker_catches_an_unpinned_helm_chart():
    bad = {"components": [{"name": "x", "plane": "foundation", "phase": 1,
                           "install_method": "helm", "app_version": "1"}]}
    assert any("chart_version" in e for e in _load_checker().validate(bad))


def test_versions_lock_matches_components():
    res = subprocess.run(
        [sys.executable, os.path.join(REPO_ROOT, "scripts", "gen-versions-lock.py"), "--check"],
        capture_output=True, text=True,
    )
    assert res.returncode == 0, res.stdout + res.stderr


def test_every_helm_application_matches_its_pin():
    """An Application's targetRevision is the pin that actually runs; components.yaml must agree."""
    import glob

    pins = {
        c["chart_name"]: str(c["chart_version"])
        for c in _components()["components"]
        if c.get("chart_name")
    }
    mismatches = []
    for path in glob.glob(os.path.join(REPO_ROOT, "solution", "platform", "**", "application.yaml"),
                          recursive=True):
        with open(path) as handle:
            app = yaml.safe_load(handle)
        source = app["spec"]["source"]
        chart = source.get("chart")
        if chart is None:
            continue
        if chart not in pins:
            mismatches.append(f"{path}: chart {chart} is not in components.yaml")
        elif str(source["targetRevision"]) != pins[chart]:
            mismatches.append(f"{path}: {chart} {source['targetRevision']} != pinned {pins[chart]}")
    assert not mismatches, "\n".join(mismatches)
