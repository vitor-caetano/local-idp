#!/usr/bin/env bash
# ABOUTME: Deletes the Kind cluster and, unless --keep-registry is given, the registry container.
# ABOUTME: Keeping the registry keeps the Backstage image, so the next build skips that step. Also
# ABOUTME: removes the cluster's root CA from the login keychain, where trust-ca.sh --install put it.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

require_tools kind docker git

keep_registry=0
[[ "${1:-}" == "--keep-registry" ]] && keep_registry=1

if kind get clusters 2>/dev/null | grep -qx "${CLUSTER_NAME}"; then
    log "Deleting Kind cluster ${CLUSTER_NAME}"
    kind delete cluster --name "${CLUSTER_NAME}" --kubeconfig "${KUBECONFIG}"
else
    log "No Kind cluster named ${CLUSTER_NAME}"
fi

if (( keep_registry )); then
    log "Keeping ${REGISTRY_NAME} and its images"
elif docker inspect "${REGISTRY_NAME}" >/dev/null 2>&1; then
    log "Removing ${REGISTRY_NAME}"
    docker rm -f "${REGISTRY_NAME}" >/dev/null
fi

# The cluster remote points at a Gitea that no longer exists.
git -C "${REPO_ROOT}" remote remove cluster 2>/dev/null || true

# The next cluster generates a new CA, so a trusted copy of this one is only stale trust.
untrust_ca
rm -f "${REPO_ROOT}/provision/local-idp-ca.crt"
log "Done."
