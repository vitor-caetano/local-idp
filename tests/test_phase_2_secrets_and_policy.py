# ABOUTME: Phase 2 gate. OpenBao feeding External Secrets, and Kyverno installed with every rule in
# ABOUTME: Audit: violations are reported, nothing is blocked.
import json

from conftest import (assert_apps_healthy, condition_true, get_json, kubectl, secret_value,
                      wait_for)


def test_secrets_and_policy_apps_healthy():
    assert_apps_healthy("openbao", "external-secrets", "openbao-config", "kyverno")


def test_policy_baseline_healthy():
    # Wave 6: it lands after the rest of the foundation, so allow it time.
    wait_for(lambda: assert_apps_healthy("policy-baseline") is None, timeout=900, interval=15,
             message="policy-baseline to be Synced and Healthy (it waits on waves 3 to 5)")


def test_clustersecretstore_ready():
    assert condition_true(get_json("get", "clustersecretstore", "openbao"), "Ready")


def test_demo_secret_materialized():
    assert secret_value("openbao", "demo-app-credentials", "username") == "local-idp"


def test_every_rule_is_audit():
    enforcing = []
    for policy in get_json("get", "clusterpolicies")["items"]:
        for rule in policy["spec"]["rules"]:
            action = rule.get("validate", {}).get("failureAction")
            if action and action != "Audit":
                enforcing.append(f"{policy['metadata']['name']}/{rule['name']}")
    assert not enforcing, f"rules enforcing before phase 7: {enforcing}"


def test_audit_admits_and_reports():
    pod = {
        "apiVersion": "v1", "kind": "Pod",
        "metadata": {"name": "phase2-audit-probe", "namespace": "apps"},
        "spec": {"containers": [{"name": "c", "image": "busybox:1.37",
                                 "command": ["sleep", "300"]}]},
    }
    kubectl("delete", "pod", "phase2-audit-probe", "-n", "apps", "--ignore-not-found")
    res = kubectl("apply", "-f", "-", input=json.dumps(pod), check=False)
    try:
        assert res.returncode == 0, f"Audit must not block admission: {res.stderr}"
        wait_for(
            lambda: any(
                r.get("policy") == "require-resource-limits" and r.get("result") == "fail"
                for report in get_json("get", "policyreports", "-n", "apps")["items"]
                for r in report.get("results", [])
            ),
            timeout=180, interval=10, message="a policy report entry for the probe pod",
        )
    finally:
        kubectl("delete", "pod", "phase2-audit-probe", "-n", "apps", "--ignore-not-found",
                "--wait=false")
