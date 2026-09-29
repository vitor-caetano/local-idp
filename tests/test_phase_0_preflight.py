# ABOUTME: Phase 0 gate. Three Ready nodes on the pinned version, nothing installed yet, and images
# ABOUTME: flowing both ways through the local registry: host push, node pull, pod reachability.
import shutil
import subprocess

import pytest

from conftest import get_json, incluster_curl, kubectl, needs_cluster, wait_for

PROBE_IMAGE = "localhost:5001/preflight/busybox:1.37"


def test_three_ready_nodes_one_ingress_ready():
    nodes = get_json("get", "nodes")["items"]
    assert len(nodes) == 3, f"expected 3 nodes, got {len(nodes)}"
    for node in nodes:
        ready = any(c["type"] == "Ready" and c["status"] == "True"
                    for c in node["status"]["conditions"])
        assert ready, f"{node['metadata']['name']} not Ready"
    ingress = [n for n in nodes if n["metadata"]["labels"].get("ingress-ready") == "true"]
    assert len(ingress) == 1, "exactly one node should carry ingress-ready=true"


def test_server_version_is_pinned_minor():
    version = get_json("version")["serverVersion"]
    assert (version["major"], version["minor"].rstrip("+")) == ("1", "36"), version


def test_cluster_is_bare():
    assert kubectl("get", "namespace", "argocd", check=False).returncode != 0, \
        "argocd already exists; phase 0 installs nothing"


def test_pod_pulls_from_localhost_5001():
    needs_cluster()
    if shutil.which("docker") is None:
        pytest.skip("docker not available to push the probe image")
    for cmd in (["docker", "pull", "busybox:1.37"],
                ["docker", "tag", "busybox:1.37", PROBE_IMAGE],
                ["docker", "push", PROBE_IMAGE]):
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        assert res.returncode == 0, f"{' '.join(cmd)}: {res.stderr}"

    kubectl("delete", "pod", "preflight-pull", "--ignore-not-found", "--wait=true")
    kubectl("run", "preflight-pull", "--restart=Never", f"--image={PROBE_IMAGE}",
            "--command", "--", "true")
    try:
        wait_for(
            lambda: get_json("get", "pod", "preflight-pull")["status"].get("phase") == "Succeeded",
            timeout=120, interval=5, message="the probe pod to pull from localhost:5001 and exit",
        )
    finally:
        kubectl("delete", "pod", "preflight-pull", "--ignore-not-found", "--wait=false")


def test_pods_reach_the_registry_by_name():
    # The CI build pushes to kind-registry:5000 from inside a pod. If CoreDNS cannot resolve the
    # container name, phase 6 fails at its build step with a DNS error.
    _, code = incluster_curl("http://kind-registry:5000/v2/")
    assert code == "200", f"kind-registry:5000 answered {code!r} from a pod"
