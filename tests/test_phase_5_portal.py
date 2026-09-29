# ABOUTME: Phase 5 gate. Backstage running on Postgres from OpenBao, every UI routed and answering
# ABOUTME: over HTTPS with the local CA, and the golden-path template in the catalog.
import json

from conftest import assert_apps_healthy, get_json, host_curl, incluster_curl, local_ca_file

HOSTS = ["argocd", "gitea", "grafana", "workflows", "backstage"]


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


def test_catalog_has_the_golden_path():
    body, code = incluster_curl(
        "http://backstage.backstage.svc:7007/api/catalog/entities/by-query",
        "--get", "--data-urlencode", "filter=kind=template,kind=group", ns="backstage",
    )
    assert code == "200", body
    names = {(e["kind"], e["metadata"]["name"]) for e in json.loads(body)["items"]}
    assert ("Template", "go-service") in names, names
    assert ("Group", "platform-team") in names, names
