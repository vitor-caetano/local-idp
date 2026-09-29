# ABOUTME: The golden-path template renders to manifests the platform will actually accept: every
# ABOUTME: kind allowed by the AppProject, the route attached to a real listener, the code tested.
import glob
import os
import shutil
import subprocess

import pytest

yaml = pytest.importorskip("yaml")

from conftest import REPO_ROOT, SOLUTION

SELF_SERVICE = os.path.join(SOLUTION, "2-self-service")
SKELETON = os.path.join(SELF_SERVICE, "go-service", "skeleton")
NAME = "hello-go"


def _render(text):
    # The template's only substitutions are ${{ values.* }}; render them as Backstage would.
    return (text.replace("${{ values.name }}", NAME)
                .replace("${{ values.description }}", "A test service")
                .replace("${{ values.owner }}", "group:default/platform-team"))


@pytest.fixture(scope="module")
def rendered(tmp_path_factory):
    out = tmp_path_factory.mktemp("rendered")
    for path in glob.glob(os.path.join(SKELETON, "**", "*"), recursive=True) + \
            glob.glob(os.path.join(SKELETON, "**", ".*"), recursive=True):
        if os.path.isdir(path):
            continue
        rel = os.path.relpath(path, SKELETON)
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(path) as handle:
            dest.write_text(_render(handle.read()))
    return out


def _manifests(rendered):
    docs = []
    for path in sorted((rendered / "manifests").glob("*.yaml")):
        docs.extend(d for d in yaml.safe_load_all(path.read_text()) if isinstance(d, dict))
    return docs


def _load(*parts):
    with open(os.path.join(SELF_SERVICE, *parts)) as handle:
        return [d for d in yaml.safe_load_all(handle) if isinstance(d, dict)]


def test_no_unrendered_template_syntax_left(rendered):
    for path in rendered.rglob("*"):
        if path.is_file():
            assert "${{" not in path.read_text(), f"{path.name} has an unknown template value"


def test_kustomization_lists_every_manifest(rendered):
    kust = yaml.safe_load((rendered / "manifests" / "kustomization.yaml").read_text())
    on_disk = {p.name for p in (rendered / "manifests").glob("*.yaml")} - {"kustomization.yaml"}
    assert set(kust["resources"]) == on_disk


def test_every_kind_is_allowed_by_the_appproject(rendered):
    # A kind missing from the whitelist makes the generated Application fail to sync with a
    # permission error, on the reader's first scaffolded service.
    project = _load("golden-path-deploy", "manifests", "appproject.yaml")[0]
    allowed = {(w["group"], w["kind"]) for w in project["spec"]["namespaceResourceWhitelist"]}
    for doc in _manifests(rendered):
        if doc["kind"] == "Kustomization":
            continue
        group = doc["apiVersion"].rpartition("/")[0]
        assert (group, doc["kind"]) in allowed, f"{doc['kind']} ({group}) not in the AppProject"


def test_route_attaches_to_a_real_listener(rendered):
    gateway = next(d for d in yaml.safe_load_all(open(os.path.join(
        SOLUTION, "1-foundation", "platform-gateway", "manifests", "gateway.yaml")))
        if isinstance(d, dict) and d.get("kind") == "Gateway")
    listeners = {l["name"] for l in gateway["spec"]["listeners"]}
    route = next(d for d in _manifests(rendered) if d["kind"] == "HTTPRoute")
    for parent in route["spec"]["parentRefs"]:
        assert parent["name"] == gateway["metadata"]["name"]
        assert parent["namespace"] == gateway["metadata"]["namespace"]
        assert parent["sectionName"] in listeners
    assert route["spec"]["hostnames"] == [f"{NAME}.localtest.me"]


def test_image_is_from_the_local_registry_with_a_tag(rendered):
    kust = yaml.safe_load((rendered / "manifests" / "kustomization.yaml").read_text())
    image = kust["images"][0]
    assert image["newName"] == f"localhost:5001/services/{NAME}"
    assert image["newTag"] and image["newTag"] != "latest"


def test_ci_pushes_where_the_manifests_pull_from():
    wt = _load("ci-pipeline", "manifests", "workflowtemplate.yaml")[0]
    build = next(t for t in wt["spec"]["templates"] if t["name"] == "build")
    output = " ".join(build["container"]["args"])
    assert "kind-registry:5000/services/{{workflow.parameters.repo-name}}" in output


def test_rendered_workload_meets_the_golden_path_policies(rendered):
    rollout = next(d for d in _manifests(rendered) if d["kind"] == "Rollout")
    pod = rollout["spec"]["template"]
    assert pod["spec"]["securityContext"]["runAsNonRoot"] is True
    assert isinstance(pod["spec"]["securityContext"]["runAsUser"], int)
    assert {"app", "version"} <= set(pod["metadata"]["labels"])
    for c in pod["spec"]["containers"]:
        assert c["resources"]["limits"]["cpu"] and c["resources"]["limits"]["memory"]
        assert "readinessProbe" in c and "livenessProbe" in c


def test_template_is_registered_where_backstage_reads_it():
    with open(os.path.join(REPO_ROOT, "images", "backstage", "app-config.production.yaml")) as handle:
        config = yaml.safe_load(handle)
    targets = [loc["target"] for loc in config["catalog"]["locations"]]
    assert "${PLATFORM_RAW_BASE}/platform/2-self-service/go-service/template.yaml" in targets
    assert "${PLATFORM_RAW_BASE}/platform/2-self-service/catalog/org.yaml" in targets


def test_rendered_service_passes_go_test(rendered):
    if shutil.which("go") is None:
        pytest.skip("go not installed")
    res = subprocess.run(["go", "vet", "./..."], cwd=rendered, capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    res = subprocess.run(["go", "test", "./..."], cwd=rendered, capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr
