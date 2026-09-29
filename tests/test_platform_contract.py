# ABOUTME: Contract tests for the reference manifests, one per defect class in AGENTS.md that can be
# ABOUTME: caught without a cluster. Each is a failure that reads Synced and Healthy on a live one.
import glob
import os

import pytest

yaml = pytest.importorskip("yaml")

from conftest import REPO_ROOT, SOLUTION

PLACEHOLDER = "REPLACE_WITH_PLATFORM_REPO_URL"


def _yaml_docs(pattern):
    for path in glob.glob(os.path.join(SOLUTION, pattern), recursive=True):
        with open(path) as handle:
            for doc in yaml.safe_load_all(handle):
                if isinstance(doc, dict):
                    yield path, doc


def _applications():
    return [(p, d) for p, d in _yaml_docs("**/application.yaml") if d.get("kind") == "Application"]


def _rel(path):
    return os.path.relpath(path, REPO_ROOT)


# --- Class 1: placeholders -----------------------------------------------------------------------

def test_every_git_sourced_application_uses_the_placeholder():
    # A hardcoded repoURL survives a Git source switch and keeps reading the old source, so half the
    # platform follows the switch and half does not, and nothing reports it.
    offenders = []
    for path, app in _applications() + [
        (p, d) for p, d in _yaml_docs("0-bootstrap/*.yaml") if d.get("kind") == "Application"
    ]:
        source = app["spec"]["source"]
        if "chart" in source:
            continue
        if source["repoURL"] != PLACEHOLDER:
            offenders.append(f"{_rel(path)}: repoURL={source['repoURL']}")
    assert not offenders, "\n".join(offenders)


def test_working_copy_has_no_unsubstituted_placeholders():
    working = os.path.join(REPO_ROOT, "platform")
    if not os.path.isdir(working):
        pytest.skip("no platform/ working copy yet")
    offenders = []
    for root, _, files in os.walk(working):
        for name in files:
            if not name.endswith((".yaml", ".yml")):
                continue
            path = os.path.join(root, name)
            with open(path) as handle:
                for lineno, line in enumerate(handle, 1):
                    if "REPLACE_WITH_" in line:
                        offenders.append(f"{_rel(path)}:{lineno}")
    assert not offenders, (
        "unsubstituted placeholders under platform/: " + ", ".join(offenders)
        + ". Run provision/set-git-source.sh."
    )


# --- Class 2: runAsNonRoot without a numeric runAsUser -------------------------------------------

def _pod_specs(doc):
    """Yield (label, pod_spec) for every pod template a workload manifest carries."""
    kind = doc.get("kind")
    spec = doc.get("spec") or {}
    if kind == "Pod":
        yield "Pod", spec
    elif kind in {"Deployment", "StatefulSet", "DaemonSet", "Job", "Rollout"}:
        yield kind, spec.get("template", {}).get("spec", {})
    elif kind == "CronJob":
        yield kind, spec.get("jobTemplate", {}).get("spec", {}).get("template", {}).get("spec", {})
    elif kind == "WorkflowTemplate":
        # securityContext at the workflow level applies to every step's pod.
        yield kind, {"securityContext": spec.get("securityContext", {}),
                     "containers": [t["container"] for t in spec.get("templates", [])
                                    if "container" in t]}


def test_run_as_non_root_always_has_a_numeric_uid():
    offenders = []
    for path, doc in _yaml_docs("**/*.yaml"):
        for label, pod in _pod_specs(doc):
            pod_sc = pod.get("securityContext") or {}
            for container in pod.get("containers", []) + pod.get("initContainers", []):
                sc = container.get("securityContext") or {}
                non_root = sc.get("runAsNonRoot", pod_sc.get("runAsNonRoot"))
                uid = sc.get("runAsUser", pod_sc.get("runAsUser"))
                if non_root and not isinstance(uid, int):
                    offenders.append(f"{_rel(path)}: {label} container {container.get('name')}")
    assert not offenders, "runAsNonRoot without a numeric runAsUser:\n" + "\n".join(offenders)


def test_helm_values_that_set_run_as_non_root_pin_a_uid():
    # The Backstage chart takes its pod security context through values, not a pod template.
    offenders = []
    for path, app in _applications():
        values = app["spec"]["source"].get("helm", {}).get("valuesObject", {})
        for key, block in _find_key(values, "podSecurityContext"):
            if block.get("runAsNonRoot") and not isinstance(block.get("runAsUser"), int):
                offenders.append(f"{_rel(path)}: {key}")
    assert not offenders, "\n".join(offenders)


def _find_key(obj, wanted, trail=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            here = f"{trail}.{k}" if trail else k
            if k == wanted and isinstance(v, dict):
                yield here, v
            yield from _find_key(v, wanted, here)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _find_key(v, wanted, f"{trail}[{i}]")


# --- Class 3: a repository that repeats the registry host ----------------------------------------

def _image_blocks(obj):
    if isinstance(obj, dict):
        img = obj.get("image")
        if isinstance(img, dict) and img.get("registry") and isinstance(img.get("repository"), str):
            yield img
        for v in obj.values():
            yield from _image_blocks(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _image_blocks(v)


def test_no_image_repository_doubles_the_registry_host():
    bad = []
    for path, app in _applications():
        for img in _image_blocks(app):
            repo, registry = img["repository"], img["registry"]
            first, _, rest = repo.partition("/")
            looks_like_host = "." in first or ":" in first or first == "localhost"
            if rest and looks_like_host:
                bad.append(f"{_rel(path)}: registry={registry} repository={repo}")
    assert not bad, "repository must not include the registry host:\n" + "\n".join(bad)


def test_backstage_image_tag_matches_the_build_script():
    # Bump one without the other and ArgoCD keeps running the old image, or pulls one never built.
    with open(os.path.join(SOLUTION, "1-foundation", "backstage", "application.yaml")) as handle:
        tag = yaml.safe_load(handle)["spec"]["source"]["helm"]["valuesObject"]["backstage"]["image"]["tag"]
    with open(os.path.join(REPO_ROOT, "images", "backstage", "build-and-push.sh")) as handle:
        script = handle.read()
    assert f'TAG="${{TAG:-{tag}}}"' in script, f"build-and-push.sh default TAG does not match {tag}"


# --- Class 5: credentials that drift ---------------------------------------------------------------

def test_seed_jobs_read_credentials_from_secrets():
    # A literal password in a Job's env is a second copy that will drift from the chart values.
    offenders = []
    for path, doc in _yaml_docs("**/manifests/*.yaml"):
        if doc.get("kind") != "Job":
            continue
        for container in doc["spec"]["template"]["spec"]["containers"]:
            for env in container.get("env", []):
                name = env["name"].upper()
                is_credential = any(word in name for word in ("PASS", "TOKEN", "SECRET"))
                if is_credential and not name.endswith("_NAME") and "value" in env:
                    offenders.append(f"{_rel(path)}: {env['name']} is a literal")
    assert not offenders, "\n".join(offenders)


# --- Structure --------------------------------------------------------------------------------

def test_every_application_uses_server_side_apply_and_a_wave():
    offenders = []
    for path, app in _applications():
        opts = app["spec"].get("syncPolicy", {}).get("syncOptions", [])
        if "ServerSideApply=true" not in opts:
            offenders.append(f"{_rel(path)}: no ServerSideApply=true")
        if "argocd.argoproj.io/sync-wave" not in app["metadata"].get("annotations", {}):
            offenders.append(f"{_rel(path)}: no sync-wave")
    assert not offenders, "\n".join(offenders)


def test_manifest_sourced_applications_point_at_their_own_directory():
    # A path typo leaves an Application Synced over an empty directory: green, and nothing applied.
    offenders = []
    for path, app in _applications():
        source = app["spec"]["source"]
        if "chart" in source:
            continue
        expected = os.path.relpath(os.path.join(os.path.dirname(path), "manifests"), SOLUTION)
        if source["path"] != "platform/" + expected:
            offenders.append(f"{_rel(path)}: path={source['path']}, expected platform/{expected}")
        if not os.path.isdir(os.path.join(os.path.dirname(path), "manifests")):
            offenders.append(f"{_rel(path)}: no manifests/ directory")
    assert not offenders, "\n".join(offenders)
