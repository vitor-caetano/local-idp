# ABOUTME: Install first, enforce last. Every Kyverno rule in the reference build ships Audit, and
# ABOUTME: every policy is scoped to the opt-in namespace label rather than the whole cluster.
import glob
import os

import pytest

yaml = pytest.importorskip("yaml")

from conftest import SOLUTION

ENROL_LABEL = "local-idp.dev/policy"


def _policies():
    for path in glob.glob(os.path.join(SOLUTION, "**", "*.yaml"), recursive=True):
        with open(path) as handle:
            for doc in yaml.safe_load_all(handle):
                if isinstance(doc, dict) and doc.get("kind") == "ClusterPolicy":
                    yield path, doc


def test_there_are_policies_to_check():
    assert len(list(_policies())) >= 7


def test_every_rule_ships_audit():
    enforcing = [
        f"{doc['metadata']['name']}/{rule['name']}"
        for _, doc in _policies()
        for rule in doc["spec"]["rules"]
        if rule.get("validate", {}).get("failureAction") != "Audit"
    ]
    assert not enforcing, (
        f"rules not in Audit: {enforcing}. The reference build ships everything Audit; phase 7 "
        "flips the golden-path set in your working copy."
    )


def test_no_policy_uses_the_deprecated_spec_level_action():
    offenders = [doc["metadata"]["name"] for _, doc in _policies()
                 if "validationFailureAction" in doc["spec"]]
    assert not offenders, f"use rule-level validate.failureAction: {offenders}"


def test_every_rule_is_scoped_to_the_enrolment_label():
    offenders = []
    for _, doc in _policies():
        for rule in doc["spec"]["rules"]:
            for block in rule["match"].get("any", []) + rule["match"].get("all", []):
                labels = block["resources"].get("namespaceSelector", {}).get("matchLabels", {})
                if labels.get(ENROL_LABEL) != "enforce":
                    offenders.append(f"{doc['metadata']['name']}/{rule['name']}")
    assert not offenders, f"rules not scoped to {ENROL_LABEL}=enforce: {offenders}"


def test_golden_path_policy_names_are_distinguishable_from_the_baseline():
    # Phase 7 flips exactly the golden-path-* set. The prefix is how both the flip and its test
    # tell the two sets apart.
    for path, doc in _policies():
        in_golden_path = f"{os.sep}golden-path-policies{os.sep}" in path
        assert doc["metadata"]["name"].startswith("golden-path-") == in_golden_path, path
