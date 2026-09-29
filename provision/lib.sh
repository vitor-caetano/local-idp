#!/usr/bin/env bash
# ABOUTME: Shared settings for the provision scripts: cluster name, kubeconfig path, registry,
# ABOUTME: and the context guard every mutating script runs before it touches anything.
# shellcheck disable=SC2034  # these are read by the scripts that source this file

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLUSTER_NAME="local-idp"
EXPECTED_CONTEXT="kind-${CLUSTER_NAME}"
# A dedicated kubeconfig, so nothing here reads or writes ~/.kube/config.
export KUBECONFIG="${LOCAL_IDP_KUBECONFIG:-${HOME}/.kube/local-idp}"

REGISTRY_NAME="kind-registry"
REGISTRY_PORT="5001"
REGISTRY_IMAGE="registry:3.1.2"

GITEA_ORG="platform"
GITEA_REPO="local-idp"
GITEA_INTERNAL_URL="http://gitea-http.gitea.svc:3000"

log() { printf '%s\n' "$*" >&2; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

require_tools() {
    local t missing=0
    for t in "$@"; do
        command -v "${t}" >/dev/null 2>&1 || { log "missing tool: ${t}"; missing=1; }
    done
    [[ "${missing}" -eq 0 ]] || die "install the missing tools (see docs/prerequisites.md)"
}

# Refuse to act on any cluster but the one this repo created.
guard_context() {
    local ctx
    ctx="$(kubectl config current-context 2>/dev/null || true)"
    [[ "${ctx}" == "${EXPECTED_CONTEXT}" ]] \
        || die "current context is '${ctx:-none}' in ${KUBECONFIG}, expected '${EXPECTED_CONTEXT}'"
}

# The mode is read from the root App-of-Apps, which set-git-source.sh keeps in step with every other
# Application, so there is one place to look.
git_source_mode() {
    local root="${REPO_ROOT}/platform/0-bootstrap/root-app.yaml"
    [[ -f "${root}" ]] || { echo "none"; return; }
    if grep -q 'REPLACE_WITH_PLATFORM_REPO_URL' "${root}"; then
        echo "unset"
    elif grep -q 'gitea-http.gitea.svc' "${root}"; then
        echo "gitea"
    else
        echo "github"
    fi
}
