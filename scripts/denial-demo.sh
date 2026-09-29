#!/usr/bin/env bash
# ABOUTME: The phase 7 denial demonstration: applies a Pod that bypasses the golden path into apps
# ABOUTME: and shows the Kyverno admission error. The one sanctioned mutating kubectl in the build.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../provision/lib.sh"

require_tools kubectl
guard_context

manifest() {
    cat <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: bypass-the-golden-path
  namespace: $1
spec:
  containers:
    - name: web
      image: docker.io/library/nginx:latest
EOF
}

log "1. A Pod pulling docker.io/library/nginx:latest into apps, where golden-path services run:"
if manifest apps | kubectl apply -f - 2>&1; then
    kubectl delete pod bypass-the-golden-path -n apps --wait=false >/dev/null
    die "it was admitted. Are the golden-path-* policies at failureAction: Enforce, and pushed?"
fi

log ""
log "2. The same Pod in default, which is not enrolled (server-side dry run, nothing is created):"
manifest default | kubectl apply --dry-run=server -f -

log ""
log "Denied in apps, admitted elsewhere: the policy is scoped by the local-idp.dev/policy label."
