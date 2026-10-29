# ABOUTME: Install first, enforce last. Every Kyverno rule ships Audit, except the golden-path set
# ABOUTME: your working copy flips in phase 7, and every policy is scoped to the opt-in namespace label.
import os

import pytest

pytest.importorskip("yaml")

from conftest import SOLUTION, tree_docs

ENROL_LABEL = "local-idp.dev/policy"


def _policies(tree):
    for path, doc in tree_docs(tree):
        if doc.get("kind") == "ClusterPolicy":
            yield path, doc


def test_there_are_policies_to_check(tree):
    assert len(list(_policies(tree))) >= 7


def test_every_rule_ships_audit(tree):
    # The reference ships everything Audit. Your working copy may hold the golden-path set at
    # Enforce once phase 7 flips it; the baseline stays Audit in both, permanently.
    enforcing = []
    for _, doc in _policies(tree):
        flippable = tree != SOLUTION and doc["metadata"]["name"].startswith("golden-path-")
        allowed = {"Audit", "Enforce"} if flippable else {"Audit"}
        enforcing += [f"{doc['metadata']['name']}/{rule['name']}"
                      for rule in doc["spec"]["rules"]
                      if rule.get("validate", {}).get("failureAction") not in allowed]
    assert not enforcing, (
        f"rules not in Audit: {enforcing}. Only the golden-path set in your working copy is ever "
        "flipped to Enforce, in phase 7."
    )


def test_no_policy_uses_the_deprecated_spec_level_action(tree):
    offenders = [doc["metadata"]["name"] for _, doc in _policies(tree)
                 if "validationFailureAction" in doc["spec"]]
    assert not offenders, f"use rule-level validate.failureAction: {offenders}"


def test_every_rule_is_scoped_to_the_enrolment_label(tree):
    offenders = []
    for _, doc in _policies(tree):
        for rule in doc["spec"]["rules"]:
            for block in rule["match"].get("any", []) + rule["match"].get("all", []):
                labels = block["resources"].get("namespaceSelector", {}).get("matchLabels", {})
                if labels.get(ENROL_LABEL) != "enforce":
                    offenders.append(f"{doc['metadata']['name']}/{rule['name']}")
    assert not offenders, f"rules not scoped to {ENROL_LABEL}=enforce: {offenders}"


def test_golden_path_policy_names_are_distinguishable_from_the_baseline(tree):
    # Phase 7 flips exactly the golden-path-* set. The prefix is how both the flip and its test
    # tell the two sets apart.
    for path, doc in _policies(tree):
        in_golden_path = f"{os.sep}golden-path-policies{os.sep}" in path
        assert doc["metadata"]["name"].startswith("golden-path-") == in_golden_path, path
