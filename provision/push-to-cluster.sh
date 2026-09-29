#!/usr/bin/env bash
# ABOUTME: Pushes your commits to the Git host inside the cluster, which is what ArgoCD reads.
# ABOUTME: The GitOps loop: commit locally, push here, watch ArgoCD reconcile.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

require_tools kubectl git curl
guard_context

LOCAL_PORT="3000"
BRANCH="${1:-main}"

if [[ "$(git_source_mode)" == "github" ]]; then
    die "platform/ points at GitHub. Push there instead: git push <your-github-remote> ${BRANCH}"
fi
git -C "${REPO_ROOT}" remote get-url cluster >/dev/null 2>&1 \
    || die 'no "cluster" remote. Run ./provision/seed-gitea.sh first.'

cleanup() {
    if [[ -n "${PF_PID:-}" ]]; then
        kill "${PF_PID}" 2>/dev/null || true
        wait "${PF_PID}" 2>/dev/null || true
    fi
}
trap cleanup EXIT

kubectl port-forward -n gitea svc/gitea-http "${LOCAL_PORT}:3000" >/dev/null 2>&1 &
PF_PID=$!
for _ in $(seq 1 15); do
    curl -fsS "http://127.0.0.1:${LOCAL_PORT}/api/v1/version" >/dev/null 2>&1 && break
    sleep 1
done
curl -fsS "http://127.0.0.1:${LOCAL_PORT}/api/v1/version" >/dev/null 2>&1 \
    || die "could not reach Gitea. Check: kubectl get pods -n gitea"

log "Pushing ${BRANCH} to the cluster"
git -C "${REPO_ROOT}" push cluster "HEAD:refs/heads/${BRANCH}"

log ""
log "Pushed. ArgoCD polls every three minutes; to see it now:"
log "    kubectl get applications -n argocd"
