# ABOUTME: Phase 5 gate. Backstage running on Postgres from OpenBao, every UI routed and answering
# ABOUTME: over HTTPS with the local CA, and the golden-path template in the catalog.
import json

from conftest import (assert_apps_healthy, get_json, host_curl, incluster_curl, local_ca_file,
                      secret_value)

HOSTS = ["argocd", "gitea", "grafana", "workflows", "backstage"]
BACKSTAGE = "http://backstage.backstage.svc:7007"
ARGOCD = "http://argo-cd-argocd-server.argocd.svc"


def test_portal_apps_healthy():
    assert_apps_healthy("backstage-config", "backstage", "platform-routes")


def test_every_route_accepted_and_resolved():
    bad = []
    for route in get_json("get", "httproutes", "-A")["items"]:
        name = f"{route['metadata']['namespace']}/{route['metadata']['name']}"
        parents = route.get("status", {}).get("parents", [])
        if not parents:
            bad.append(f"{name}: no parent status")
        for parent in parents:
            for cond in parent.get("conditions", []):
                if cond["type"] in ("Accepted", "ResolvedRefs") and cond["status"] != "True":
                    bad.append(f"{name}: {cond['type']}={cond['status']} {cond.get('message', '')}")
    assert not bad, "\n".join(bad)


def test_every_ui_answers_over_https():
    ca = local_ca_file()
    bad = []
    for host in HOSTS:
        _, code = host_curl(f"https://{host}.localtest.me/", "--cacert", ca, "-o", "/dev/null")
        if not code.startswith(("2", "3")):
            bad.append(f"{host}: {code}")
    assert not bad, "UIs not answering: " + ", ".join(bad)


def _guest_token():
    # The backend refuses unauthenticated calls. Sign in as guest, the way the browser does.
    body, code = incluster_curl(
        f"{BACKSTAGE}/api/auth/guest/refresh?optional&env=production",
        "-H", "X-Requested-With: XMLHttpRequest", ns="backstage",
    )
    assert code == "200", f"guest sign-in failed: {body}"
    return json.loads(body)["backstageIdentity"]["token"]


def test_catalog_has_the_golden_path():
    token = _guest_token()
    body, code = incluster_curl(
        f"{BACKSTAGE}/api/catalog/entities/by-query",
        "-H", f"Authorization: Bearer {token}",
        "--get", "--data-urlencode", "filter=kind=template,kind=group", ns="backstage",
    )
    assert code == "200", body
    names = {(e["kind"], e["metadata"]["name"]) for e in json.loads(body)["items"]}
    assert ("Template", "go-service") in names, names
    assert ("Group", "platform-team") in names, names


def test_argocd_token_signs_in_as_the_backstage_account():
    token = secret_value("backstage", "argocd-credentials", "token")
    body, code = incluster_curl(
        f"{ARGOCD}/api/v1/session/userinfo", "-H", f"Authorization: Bearer {token}", ns="backstage",
    )
    assert code == "200", body
    info = json.loads(body)
    assert info.get("loggedIn") is True and info.get("username") == "backstage", info


def test_backstage_reads_argocd_through_its_proxy():
    body, code = incluster_curl(
        f"{BACKSTAGE}/api/proxy/argocd/api/applications/backstage",
        "-H", f"Authorization: Bearer {_guest_token()}", ns="backstage",
    )
    assert code == "200", f"the ArgoCD proxy answered {code}: {body[:300]}"
    assert json.loads(body)["metadata"]["name"] == "backstage"
