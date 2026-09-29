# ABOUTME: Phase 6 gate. The self-service plane is up, and a service scaffolded from Backstage went
# ABOUTME: through CI, into the registry, out through ArgoCD, and answers at its hostname.
import json

import pytest

from conftest import (assert_apps_healthy, get_json, host_curl, incluster_curl, kubectl,
                      local_ca_file, secret_value)

SERVICE = "hello-go"


def test_self_service_apps_healthy():
    assert_apps_healthy("platform-self-service", "ci-pipeline", "golden-path-deploy",
                        "golden-path-policies")


@pytest.mark.parametrize("kind,name", [("eventbus", "default"), ("eventsource", "gitea"),
                                       ("sensor", "ci-go-service")])
def test_events_deployed(kind, name):
    conds = get_json("get", kind, name, "-n", "argo-events").get("status", {}).get("conditions", [])
    assert conds and all(c["status"] == "True" for c in conds), conds


@pytest.fixture(scope="module")
def scaffolded():
    user = secret_value("gitea", "gitea-seed-creds", "username")
    password = secret_value("gitea", "gitea-seed-creds", "password")
    _, code = incluster_curl(f"http://gitea-http.gitea.svc:3000/api/v1/repos/services/{SERVICE}",
                             "-u", f"{user}:{password}", ns="gitea")
    if code != "200":
        pytest.skip(f"scaffold '{SERVICE}' from the go-service template in Backstage first")


def test_ci_workflow_succeeded(scaffolded):
    runs = [
        w for w in get_json("get", "workflows", "-n", "ci")["items"]
        if any(p.get("value") == SERVICE
               for p in w["spec"].get("arguments", {}).get("parameters", []))
    ]
    assert runs, f"no CI Workflow ran for {SERVICE}; check the webhook and the Sensor logs"
    assert any(w.get("status", {}).get("phase") == "Succeeded" for w in runs), \
        [w.get("status", {}).get("phase") for w in runs]


def test_image_in_the_registry(scaffolded):
    body, code = incluster_curl(f"http://kind-registry:5000/v2/services/{SERVICE}/tags/list")
    assert code == "200", body
    assert json.loads(body).get("tags"), "no tags pushed"


def test_deployed_and_healthy(scaffolded):
    assert_apps_healthy(f"svc-{SERVICE}")
    rollout = get_json("get", "rollout", SERVICE, "-n", "apps")
    assert rollout.get("status", {}).get("phase") == "Healthy", rollout.get("status")


def test_answers_at_its_hostname(scaffolded):
    body, code = host_curl(f"https://{SERVICE}.localtest.me/", "--cacert", local_ca_file())
    assert code == "200", body
    assert f"hello from {SERVICE}" in body


def test_prometheus_scrapes_it(scaffolded):
    body, code = incluster_curl(
        "http://kube-prometheus-stack-prometheus.observability.svc:9090/api/v1/query",
        "--get", "--data-urlencode", f'query=http_requests_total{{service="{SERVICE}"}}',
        ns="observability",
    )
    assert code == "200", body
    assert json.loads(body)["data"]["result"], "no http_requests_total series for the service"
