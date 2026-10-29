# ABOUTME: The Backstage ArgoCD and Kubernetes tabs are wired to data they can find: a read-only
# ABOUTME: ArgoCD token minted into the Secret Backstage reads, and selectors that match real labels.
import os

import pytest

yaml = pytest.importorskip("yaml")

from conftest import REPO_ROOT, tree_docs

ARGOCD_EXTENSIONS = (
    "entity-content:argocd/ArgoCdPage",
    "entity-card:argocd/overviewCard",
    "entity-card:argocd/historyCard",
)


def _backstage_values(tree):
    with open(os.path.join(tree, "1-foundation", "backstage", "application.yaml")) as handle:
        return yaml.safe_load(handle)["spec"]["source"]["helm"]["valuesObject"]["backstage"]


def _argocd_values(tree):
    with open(os.path.join(tree, "0-bootstrap", "argocd-values.yaml")) as handle:
        return yaml.safe_load(handle)["configs"]


def test_backstage_reads_the_argocd_token_from_the_minted_secret(tree):
    env = {e["name"]: e for e in _backstage_values(tree).get("extraEnvVars", [])}
    assert "ARGOCD_AUTH_TOKEN" in env, "Backstage has no ARGOCD_AUTH_TOKEN; the ArgoCD tab gets 401"
    secret = env["ARGOCD_AUTH_TOKEN"]["valueFrom"]["secretKeyRef"]["name"]

    # Something in backstage-config has to write that Secret, or Backstage never starts.
    writers = [
        doc["metadata"]["name"]
        for _, doc in tree_docs(tree, "1-foundation/backstage-config/manifests/*.yaml")
        if doc.get("kind") == "Job" and secret in yaml.safe_dump(doc["spec"])
    ]
    assert writers, f"no Job in backstage-config writes the {secret} Secret"

    with open(os.path.join(REPO_ROOT, "images", "backstage", "app-config.production.yaml")) as h:
        assert "${ARGOCD_AUTH_TOKEN}" in h.read(), "the image's ArgoCD proxy does not send the token"


def test_backstage_argocd_account_is_read_only(tree):
    configs = _argocd_values(tree)
    assert configs["cm"].get("accounts.backstage") == "apiKey", "no backstage account to mint for"
    policy = configs["rbac"]["policy.csv"].splitlines()
    roles = {line.split(",")[2].strip() for line in policy
             if line.startswith("g,") and line.split(",")[1].strip() == "backstage"}
    assert roles, "the backstage account is bound to no role"
    actions = [line.split(",")[3].strip() for line in policy
               if line.startswith("p,") and line.split(",")[1].strip() in roles]
    assert actions and set(actions) == {"get"}, f"backstage role allows more than get: {actions}"


def test_argocd_tab_and_cards_show_only_where_there_is_an_application(tree):
    # app.packages: all discovers the Roadie plugin with no filter: the tab appears on every entity.
    extensions = _backstage_values(tree).get("appConfig", {}).get("app", {}).get("extensions", [])
    filters = {}
    for ext in extensions:
        if isinstance(ext, dict):
            for ext_id, body in ext.items():
                filters[ext_id] = ((body or {}).get("config") or {}).get("filter")
    for ext_id in ARGOCD_EXTENSIONS:
        assert filters.get(ext_id) == {"metadata.annotations.argocd/app-name": {"$exists": True}}, (
            f"{ext_id} is not limited to entities annotated argocd/app-name"
        )


def test_skeleton_kubernetes_selector_matches_its_labels(tree):
    # The Kubernetes plugin finds resources by label, not by backstage.io/kubernetes-id.
    skeleton = os.path.join(tree, "2-self-service", "go-service", "skeleton")
    with open(os.path.join(skeleton, "catalog-info.yaml")) as handle:
        annotations = yaml.safe_load(handle)["metadata"]["annotations"]
    selector = annotations.get("backstage.io/kubernetes-label-selector")
    assert selector, "catalog-info.yaml has no backstage.io/kubernetes-label-selector"
    key, _, value = selector.partition("=")

    rollout = next(doc for _, doc in tree_docs(skeleton, "manifests/*.yaml")
                   if doc.get("kind") == "Rollout")
    pod_labels = rollout["spec"]["template"]["metadata"]["labels"]
    assert pod_labels.get(key) == value, f"selector {selector} matches no pod label: {pod_labels}"
