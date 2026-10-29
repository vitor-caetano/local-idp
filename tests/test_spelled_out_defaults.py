# ABOUTME: Build rule 9. Manifests carry the defaults the cluster adds, so ArgoCD reaches Synced
# ABOUTME: without ignoreDifferences, which would also hide a deliberate change to the same field.
import os

import pytest

yaml = pytest.importorskip("yaml")

from conftest import REPO_ROOT, tree_docs

# What the pinned ESO and Kyverno webhooks fill in when a manifest leaves it out.
EXTERNAL_SECRET_TARGET = {"creationPolicy", "deletionPolicy"}
EXTERNAL_SECRET_REMOTE_REF = {"conversionStrategy", "decodingStrategy", "metadataPolicy",
                              "nullBytePolicy"}
CLUSTER_POLICY_SPEC = {"admission", "background", "emitWarning"}

# The only cluster-wide ignores argocd-values.yaml may carry: fields that cannot live in Git.
GLOBAL_IGNORES = {
    "resource.customizations.ignoreDifferences.apiextensions.k8s.io_CustomResourceDefinition",
    "resource.customizations.ignoreDifferences.kyverno.io_ClusterPolicy",
}


def _rel(path):
    return os.path.relpath(path, REPO_ROOT)


def _application_specs(doc):
    if doc.get("kind") == "Application":
        yield doc.get("spec") or {}
    elif doc.get("kind") == "ApplicationSet":
        yield (doc.get("spec") or {}).get("template", {}).get("spec") or {}


def test_no_application_ignores_differences(tree):
    offenders = [
        f"{_rel(path)}: {doc['metadata']['name']}"
        for path, doc in tree_docs(tree)
        for spec in _application_specs(doc)
        if "ignoreDifferences" in spec
    ]
    assert not offenders, (
        "spell the defaulted fields out in the manifests instead (build rule 9):\n"
        + "\n".join(offenders)
    )


def test_global_ignores_match_only_what_the_cluster_adds(tree):
    with open(os.path.join(tree, "0-bootstrap", "argocd-values.yaml")) as handle:
        cm = yaml.safe_load(handle)["configs"]["cm"]
    ignores = {k: yaml.safe_load(v) for k, v in cm.items()
               if k.startswith("resource.customizations.ignoreDifferences.")}
    assert set(ignores) <= GLOBAL_IGNORES, (
        f"unexpected cluster-wide ignores: {sorted(set(ignores) - GLOBAL_IGNORES)}. "
        "Spell the field out in the manifest instead."
    )
    for key, rule in ignores.items():
        # A bare path ignores every value; a select() guard ignores only the one the cluster adds.
        for expr in rule.get("jqPathExpressions", []):
            assert "select(" in expr, f"{key}: '{expr}' ignores any value, not just the default"
    policy = ignores.get("resource.customizations.ignoreDifferences.kyverno.io_ClusterPolicy")
    if policy:
        # Safe unguarded: test_policies.py forbids the field in Git, so any value is Kyverno's.
        assert policy == {"jsonPointers": ["/spec/validationFailureAction"]}, policy


def test_external_secrets_spell_out_webhook_defaults(tree):
    offenders = []
    for path, doc in tree_docs(tree):
        if doc.get("kind") != "ExternalSecret":
            continue
        name = f"{_rel(path)}: {doc['metadata']['name']}"
        missing = EXTERNAL_SECRET_TARGET - set(doc["spec"].get("target", {}))
        if missing:
            offenders.append(f"{name} target lacks {sorted(missing)}")
        for item in doc["spec"].get("data", []):
            missing = EXTERNAL_SECRET_REMOTE_REF - set(item["remoteRef"])
            if missing:
                offenders.append(f"{name} {item['secretKey']} remoteRef lacks {sorted(missing)}")
    assert not offenders, "\n".join(offenders)


def test_cluster_policies_spell_out_webhook_defaults(tree):
    offenders = []
    for path, doc in tree_docs(tree):
        if doc.get("kind") != "ClusterPolicy":
            continue
        name = f"{_rel(path)}: {doc['metadata']['name']}"
        missing = CLUSTER_POLICY_SPEC - set(doc["spec"])
        if missing:
            offenders.append(f"{name} spec lacks {sorted(missing)}")
        for rule in doc["spec"]["rules"]:
            if "skipBackgroundRequests" not in rule:
                offenders.append(f"{name}/{rule['name']} lacks skipBackgroundRequests")
            if "validate" in rule and "allowExistingViolations" not in rule["validate"]:
                offenders.append(f"{name}/{rule['name']} validate lacks allowExistingViolations")
    assert not offenders, "\n".join(offenders)
