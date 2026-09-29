# ABOUTME: Phase 1 gate. ArgoCD reconciling from Git, the local CA issuing, and the Gateway reachable
# ABOUTME: from this machine through Kind's port mapping.
from conftest import assert_apps_healthy, condition_true, get_json, host_curl


def test_argocd_pods_ready():
    pods = get_json("get", "pods", "-n", "argocd", "-l", "app.kubernetes.io/part-of=argocd")["items"]
    assert pods, "no ArgoCD pods found"
    for pod in pods:
        assert condition_true(pod, "Ready"), f"ArgoCD pod not Ready: {pod['metadata']['name']}"


def test_foundation_root_synced():
    app = get_json("get", "application", "platform-foundation", "-n", "argocd")
    assert app["status"]["sync"]["status"] == "Synced"
    assert "REPLACE_WITH" not in app["spec"]["source"]["repoURL"]


def test_wave_0_to_2_traffic_components_healthy():
    assert_apps_healthy("platform-namespaces", "cert-manager", "envoy-gateway", "gitea",
                        "cert-manager-issuers", "platform-gateway")


def test_local_ca_issues_the_wildcard():
    assert condition_true(get_json("get", "clusterissuer", "local-idp-ca"), "Ready")
    cert = get_json("get", "certificate", "wildcard-localtest-me", "-n", "platform-gateway")
    assert condition_true(cert, "Ready")


def test_gateway_programmed_on_fixed_nodeports():
    gw = get_json("get", "gateway", "platform-gateway", "-n", "platform-gateway")
    assert condition_true(gw, "Programmed"), gw.get("status")
    services = get_json("get", "svc", "-n", "envoy-gateway-system",
                        "-l", "gateway.envoyproxy.io/owning-gateway-name=platform-gateway")["items"]
    assert len(services) == 1, "expected one Envoy Service for platform-gateway"
    svc = services[0]["spec"]
    assert svc["type"] == "NodePort"
    ports = {p["port"]: p.get("nodePort") for p in svc["ports"]}
    assert ports.get(80) == 30080 and ports.get(443) == 30443, ports


def test_http_redirects_to_https_from_the_host():
    _, code = host_curl("http://gitea.localtest.me/")
    assert code == "301", f"expected the redirect route to answer 301, got {code!r}"
