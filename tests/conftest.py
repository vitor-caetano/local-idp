# ABOUTME: Shared pytest helpers. All cluster access goes through an explicit kubeconfig and a
# ABOUTME: context guard, never the default one, and cluster tests skip when none is given.
import base64
import json
import os
import re
import subprocess
import tempfile
import time

import pytest

KUBECONFIG_FILE = os.environ.get("KUBECONFIG_FILE", "")
EXPECTED_CONTEXT = os.environ.get("EXPECTED_CONTEXT", "")
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOLUTION = os.path.join(REPO_ROOT, "solution", "platform")


def _run(args, timeout=60, **kwargs):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, **kwargs)


def needs_cluster():
    if not KUBECONFIG_FILE:
        pytest.skip("KUBECONFIG_FILE not set; cluster tests skipped")


@pytest.fixture(scope="session", autouse=True)
def _guard_context():
    """Refuse to run against any cluster but the expected one."""
    if not KUBECONFIG_FILE:
        return
    res = _run(["kubectl", "--kubeconfig", KUBECONFIG_FILE, "config", "current-context"])
    ctx = res.stdout.strip()
    if EXPECTED_CONTEXT and ctx != EXPECTED_CONTEXT:
        pytest.exit(
            f"ABORT: context '{ctx}' does not match EXPECTED_CONTEXT '{EXPECTED_CONTEXT}'",
            returncode=2,
        )


def kubectl(*args, check=True, timeout=60, input=None):
    """Run kubectl bound to the explicit kubeconfig. Skips if none is set."""
    needs_cluster()
    res = _run(["kubectl", "--kubeconfig", KUBECONFIG_FILE, *args], timeout=timeout, input=input)
    if check and res.returncode != 0:
        raise AssertionError(f"kubectl {' '.join(args)} failed: {res.stderr.strip()}")
    return res


def get_json(*args):
    return json.loads(kubectl(*args, "-o", "json").stdout)


def secret_value(namespace, name, key):
    data = get_json("get", "secret", name, "-n", namespace).get("data", {})
    assert key in data, f"secret {namespace}/{name} has no key {key}"
    return base64.b64decode(data[key]).decode()


def app_status(name):
    status = get_json("get", "application", name, "-n", "argocd").get("status", {})
    return status.get("sync", {}).get("status"), status.get("health", {}).get("status")


def assert_apps_healthy(*names):
    bad = []
    for name in names:
        res = kubectl("get", "application", name, "-n", "argocd", check=False)
        if res.returncode != 0:
            bad.append(f"{name}=missing")
            continue
        sync, health = app_status(name)
        if sync != "Synced" or health != "Healthy":
            bad.append(f"{name}={sync}/{health}")
    assert not bad, "not Synced/Healthy: " + ", ".join(bad)


def condition_true(obj, cond_type):
    conds = obj.get("status", {}).get("conditions", [])
    return any(c.get("type") == cond_type and c.get("status") == "True" for c in conds)


def crd_established(name):
    return condition_true(get_json("get", "crd", name), "Established")


def wait_for(predicate, timeout=300, interval=10, message="condition"):
    """Poll predicate until it returns truthy, or fail with message."""
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            last = predicate()
            if last:
                return last
        except AssertionError as err:
            last = err
        time.sleep(interval)
    pytest.fail(f"timed out after {timeout}s waiting for {message} (last: {last})")


# kubectl run --rm appends its deletion notice to stdout with no separator.
_KUBECTL_DELETION_NOTICE = re.compile(r'\s*pod "[^"]+" deleted(?: from \S+ namespace)?\s*$')


def incluster_curl(url, *curl_args, ns="default", timeout=120):
    """One-shot in-cluster curl. Returns (body, http_code)."""
    pod = "phasetest-curl-" + str(abs(hash((url, curl_args))) % 100000)
    # -i is required: kubectl run --rm only streams stdout back, and reliably deletes the pod,
    # when attached.
    res = kubectl(
        "run", pod, "-n", ns, "--rm", "-i", "--restart=Never",
        "--image=curlimages/curl:8.11.0", "--command", "--",
        "curl", "-sS", "-m", "30", "-w", "\\n%{http_code}", *curl_args, url,
        check=False, timeout=timeout,
    )
    out = _KUBECTL_DELETION_NOTICE.sub("", res.stdout).rstrip("\n")
    body, _, code = out.rpartition("\n")
    return body, code


def local_ca_file():
    """Write the platform's root CA to a temp file and return its path."""
    pem = secret_value("cert-manager", "local-idp-root-ca", "ca.crt")
    handle = tempfile.NamedTemporaryFile("w", suffix=".crt", delete=False)
    handle.write(pem)
    handle.close()
    return handle.name


def host_curl(url, *curl_args, timeout=60):
    """curl from this machine, through Kind's port mapping. Returns (body, http_code)."""
    needs_cluster()
    res = _run(
        ["curl", "-sS", "-m", "30", "-w", "\n%{http_code}", *curl_args, url], timeout=timeout,
    )
    body, _, code = res.stdout.rpartition("\n")
    return body, code
