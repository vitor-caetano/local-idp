#!/usr/bin/env bash
# ABOUTME: Quick read-only health summary: every Application's sync and health, and every UI's HTTPS
# ABOUTME: status code through the Gateway. Safe to run at any point in the build.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../provision/lib.sh"

require_tools kubectl curl base64
guard_context

log "== Applications"
kubectl get applications -n argocd \
    -o custom-columns='NAME:.metadata.name,SYNC:.status.sync.status,HEALTH:.status.health.status,WAVE:.metadata.annotations.argocd\.argoproj\.io/sync-wave'

ca="$(mktemp)"
trap 'rm -f "${ca}"' EXIT
if kubectl get secret local-idp-root-ca -n cert-manager -o jsonpath='{.data.ca\.crt}' 2>/dev/null \
        | base64 -d > "${ca}" && [[ -s "${ca}" ]]; then
    log ""
    log "== UIs"
    for host in argocd gitea grafana workflows backstage; do
        code="$(curl -s -o /dev/null -m 10 -w '%{http_code}' --cacert "${ca}" "https://${host}.localtest.me/" || true)"
        printf '  %-10s %s\n' "${host}" "${code}"
    done
else
    log ""
    log "(no local CA yet; UIs not checked)"
fi
