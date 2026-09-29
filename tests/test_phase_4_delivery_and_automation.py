# ABOUTME: Phase 4 gate. Argo Workflows runs a Workflow in ci, Rollouts and KEDA CRDs exist, and
# ABOUTME: gitea-config has handed out the token and wired the org webhook.
import json

from conftest import (assert_apps_healthy, crd_established, get_json, incluster_curl, kubectl,
                      secret_value, wait_for)


def test_delivery_apps_healthy():
    assert_apps_healthy("argo-workflows", "argo-events", "argo-rollouts", "keda", "gitea-config")


def test_hello_workflow_succeeds_in_ci():
    wf = {
        "apiVersion": "argoproj.io/v1alpha1", "kind": "Workflow",
        "metadata": {"generateName": "phase4-hello-", "namespace": "ci"},
        "spec": {
            "serviceAccountName": "ci-runner", "entrypoint": "hello",
            "securityContext": {"runAsNonRoot": True, "runAsUser": 1000},
            "templates": [{"name": "hello", "container": {
                "image": "busybox:1.37", "command": ["echo", "hello from ci"]}}],
        },
    }
    name = kubectl("create", "-f", "-", "-o", "name", input=json.dumps(wf)).stdout.strip()
    try:
        phase = wait_for(
            lambda: get_json("get", name, "-n", "ci").get("status", {}).get("phase")
            in ("Succeeded", "Failed", "Error") and get_json("get", name, "-n", "ci")["status"]["phase"],
            timeout=300, interval=10, message="the hello Workflow to finish",
        )
        assert phase == "Succeeded", get_json("get", name, "-n", "ci")["status"]
    finally:
        kubectl("delete", name, "-n", "ci", "--ignore-not-found", "--wait=false")


def test_rollouts_and_keda_crds():
    assert crd_established("rollouts.argoproj.io")
    assert crd_established("scaledobjects.keda.sh")


def test_automation_token_handed_out():
    assert secret_value("argocd", "gitea-scm-token", "token")
    assert secret_value("ci", "gitea-ci-credentials", "token")


def test_services_org_has_the_ci_webhook():
    user = secret_value("gitea", "gitea-seed-creds", "username")
    password = secret_value("gitea", "gitea-seed-creds", "password")
    body, code = incluster_curl("http://gitea-http.gitea.svc:3000/api/v1/orgs/services/hooks",
                                "-u", f"{user}:{password}", ns="gitea")
    assert code == "200", body
    urls = [h["config"]["url"] for h in json.loads(body)]
    assert "http://gitea-eventsource-svc.argo-events.svc:12000/push" in urls, urls
