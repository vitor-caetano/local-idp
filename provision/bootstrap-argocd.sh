#!/usr/bin/env bash
# ABOUTME: Installs ArgoCD with Helm, the one direct install. Everything after this flows through
# ABOUTME: Git. Uses the values in platform/0-bootstrap so the health checks ship from day one.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

require_tools helm kubectl
guard_context

VALUES="${REPO_ROOT}/platform/0-bootstrap/argocd-values.yaml"
[[ -f "${VALUES}" ]] || die "${VALUES} not found. Create platform/ first."

# Pinned in components.yaml. Read it from there so the two cannot disagree.
CHART_VERSION="$(grep -A8 'name: argo-cd$' "${REPO_ROOT}/components.yaml" \
    | sed -n 's/^ *chart_version: *"\([^"]*\)"/\1/p' | head -1)"
[[ -n "${CHART_VERSION}" ]] || die "could not read the argo-cd chart_version from components.yaml"

log "Installing argo-cd chart ${CHART_VERSION} into argocd"
helm upgrade --install argo-cd argo-cd \
    --repo https://argoproj.github.io/argo-helm \
    --version "${CHART_VERSION}" \
    --namespace argocd --create-namespace \
    --values "${VALUES}" \
    --wait --timeout 10m

cat <<EOF

ArgoCD is up. Nothing is syncing yet: there is no Git host for it to read.
Admin password:
    kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d

Next: ./images/backstage/build-and-push.sh, then ./provision/seed-gitea.sh
EOF
