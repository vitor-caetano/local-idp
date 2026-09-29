# ABOUTME: Phase 7 gate. The golden-path policies enforce, the baseline still audits, a workload that
# ABOUTME: bypasses the golden path is denied in apps only, and the scaffolded service still runs.
import json

from conftest import assert_apps_healthy, get_json, kubectl

BYPASS_POD = {
    "apiVersion": "v1", "kind": "Pod",
    "metadata": {"name": "phase7-bypass"},
    "spec": {"containers": [{"name": "c", "image": "docker.io/library/nginx:latest"}]},
}


def _actions(prefix, want_prefix):
    out = {}
    for policy in get_json("get", "clusterpolicies")["items"]:
        name = policy["metadata"]["name"]
        if name.startswith(prefix) == want_prefix:
            for rule in policy["spec"]["rules"]:
                out[f"{name}/{rule['name']}"] = rule.get("validate", {}).get("failureAction")
    return out


def _dry_run(namespace):
    pod = dict(BYPASS_POD, metadata={"name": "phase7-bypass", "namespace": namespace})
    return kubectl("apply", "--dry-run=server", "-f", "-", input=json.dumps(pod), check=False)


def test_golden_path_policies_enforce():
    actions = _actions("golden-path-", True)
    assert len(actions) >= 3
    assert set(actions.values()) == {"Enforce"}, actions


def test_baseline_still_audits():
    actions = _actions("golden-path-", False)
    assert actions and set(actions.values()) == {"Audit"}, actions


def test_bypass_denied_in_apps():
    res = _dry_run("apps")
    assert res.returncode != 0, "a docker.io:latest pod was admitted into apps"
    assert "golden-path-restrict-registries" in res.stderr, res.stderr


def test_bypass_admitted_outside_apps():
    res = _dry_run("default")
    assert res.returncode == 0, f"policy scope leaked outside apps: {res.stderr}"


def test_golden_path_service_still_healthy():
    assert_apps_healthy("svc-hello-go")
