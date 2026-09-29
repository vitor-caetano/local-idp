# ABOUTME: Every custom resource the platform waits on is assessable by ArgoCD, by a built-in check
# ABOUTME: or one in argocd-values.yaml. Otherwise ArgoCD reports it Healthy whatever it is doing.
import glob
import os

import pytest

yaml = pytest.importorskip("yaml")

from conftest import REPO_ROOT, SOLUTION

VALUES = os.path.join(SOLUTION, "0-bootstrap", "argocd-values.yaml")
SKELETON = os.path.join(SOLUTION, "2-self-service", "go-service", "skeleton")

# Kinds with a custom check in argocd-values.yaml, mapped to the key.
CUSTOM = {
    "Application": "resource.customizations.health.argoproj.io_Application",
    "Gateway": "resource.customizations.health.gateway.networking.k8s.io_Gateway",
    "HTTPRoute": "resource.customizations.health.gateway.networking.k8s.io_HTTPRoute",
    "EventBus": "resource.customizations.health.argoproj.io_EventBus",
    "EventSource": "resource.customizations.health.argoproj.io_EventSource",
    "Sensor": "resource.customizations.health.argoproj.io_Sensor",
}

# Kinds ArgoCD 3.x assesses with a check it ships (resource_customizations in the argo-cd repo).
BUILT_IN = {
    "Rollout", "ScaledObject", "ExternalSecret", "ClusterSecretStore", "Certificate",
    "ClusterIssuer", "ClusterPolicy",
}

# Kinds with no readiness the platform waits on: configuration, RBAC, definitions, and core kinds
# ArgoCD assesses itself.
EXEMPT = {
    "ApplicationSet", "AppProject", "GatewayClass", "EnvoyProxy", "Namespace", "ConfigMap",
    "Secret", "ServiceAccount", "Service", "Role", "RoleBinding", "ClusterRole",
    "ClusterRoleBinding", "Deployment", "StatefulSet", "Job", "Pod", "WorkflowTemplate",
    "ServiceMonitor", "Kustomization", "Component", "Template", "Group",
}


def _customizations():
    with open(VALUES) as handle:
        return yaml.safe_load(handle)["configs"]["cm"]


def test_every_custom_check_is_present():
    missing = [k for k, key in CUSTOM.items() if key not in _customizations()]
    assert not missing, f"no ArgoCD health check for {missing}"


def test_custom_checks_handle_a_resource_with_no_status():
    for kind, key in CUSTOM.items():
        script = _customizations()[key]
        assert "obj.status ~= nil" in script, f"{kind} check does not guard against a nil status"
        assert script.strip().endswith("return hs"), f"{kind} check has no terminal return"


def test_custom_checks_can_report_not_healthy():
    for kind, key in CUSTOM.items():
        assert '"Progressing"' in _customizations()[key], f"{kind} check can only return Healthy"


def test_every_shipped_kind_is_accounted_for():
    """Guard the lists, so a new kind cannot slip in unassessed."""
    found = set()
    for path in glob.glob(os.path.join(SOLUTION, "**", "*.yaml"), recursive=True):
        with open(path) as handle:
            try:
                docs = list(yaml.safe_load_all(handle))
            except yaml.YAMLError:
                continue
        for doc in docs:
            if isinstance(doc, dict) and doc.get("kind"):
                found.add(doc["kind"])
    unaccounted = sorted(found - set(CUSTOM) - BUILT_IN - EXEMPT)
    assert not unaccounted, (
        f"kinds with no health decision: {unaccounted}. Add a check to argocd-values.yaml and "
        "CUSTOM, or list them in BUILT_IN or EXEMPT with a reason."
    )
