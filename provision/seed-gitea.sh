#!/usr/bin/env bash
# ABOUTME: Installs the in-cluster Git host, seeds it with your platform tree, and starts ArgoCD.
# ABOUTME: Breaks the bootstrap cycle: the platform is read from Gitea, but Gitea's chart is not.
#
# Gitea's own Application pulls its chart from dl.gitea.com, so it is the one Application that can
# be applied before a Git host exists. It is applied directly, the repo is seeded, and only then does
# ArgoCD get the root App-of-Apps.
#
# In GitHub mode (set-git-source.sh github ...) Gitea is still installed, because the golden-path
# service repos live there, but the platform tree is not pushed to it.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

require_tools kubectl git curl
guard_context

GITEA_APP="${REPO_ROOT}/platform/1-foundation/gitea/application.yaml"
ROOT_APP="${REPO_ROOT}/platform/0-bootstrap/root-app.yaml"
LOCAL_PORT="3000"

for f in "${GITEA_APP}" "${ROOT_APP}"; do
    [[ -f "${f}" ]] || die "${f} not found. Create your working copy first: cp -a solution/platform/. platform/"
done

mode="$(git_source_mode)"
[[ "${mode}" == "gitea" || "${mode}" == "github" ]] \
    || die "platform/ has no Git source yet. Run ./provision/set-git-source.sh gitea"
if grep -rq --include='*.yaml' --include='*.yml' 'REPLACE_WITH_' "${REPO_ROOT}/platform"; then
    die "platform/ still has unsubstituted placeholders. Run ./provision/set-git-source.sh"
fi
if [[ -n "$(git -C "${REPO_ROOT}" status --porcelain platform)" ]]; then
    die "platform/ has uncommitted changes. ArgoCD reads commits, not your working tree. Commit first."
fi

cleanup() {
    if [[ -n "${PF_PID:-}" ]]; then
        kill "${PF_PID}" 2>/dev/null || true
        wait "${PF_PID}" 2>/dev/null || true
    fi
}
trap cleanup EXIT

# --- 1. Install Gitea ---------------------------------------------------------------------------
log "[1/5] Installing Gitea"
kubectl apply -n argocd -f "${GITEA_APP}"

# --- 2. Derive the seed credentials from the chart values ---------------------------------------
# gitea-config's seed Job reads gitea-seed-creds. Deriving it from the Application that sets the
# admin account means the two cannot disagree (defect class 5).
log "[2/5] Deriving gitea-seed-creds from the chart values"
ADMIN_USER="$(grep -A4 '^ *admin:' "${GITEA_APP}" | sed -n 's/^ *username: *//p' | head -1)"
ADMIN_PASS="$(grep -A4 '^ *admin:' "${GITEA_APP}" | sed -n 's/^ *password: *"\{0,1\}\([^"]*\)"\{0,1\}$/\1/p' | head -1)"
[[ -n "${ADMIN_USER}" && -n "${ADMIN_PASS}" ]] || die "could not read the Gitea admin account from ${GITEA_APP}"
kubectl create namespace gitea --dry-run=client -o yaml | kubectl apply -f - >/dev/null
kubectl create secret generic gitea-seed-creds \
    --namespace gitea \
    --from-literal=username="${ADMIN_USER}" \
    --from-literal=password="${ADMIN_PASS}" \
    --dry-run=client -o yaml | kubectl apply -f - >/dev/null

# --- 3. Wait for it to answer -------------------------------------------------------------------
log "[3/5] Waiting for Gitea (up to 5 minutes)"
for _ in $(seq 1 60); do
    kubectl get deployment/gitea -n gitea >/dev/null 2>&1 && break
    sleep 5
done
kubectl wait --for=condition=available --timeout=300s -n gitea deployment/gitea >/dev/null \
    || die "Gitea did not become available. Check: kubectl get pods -n gitea"

kubectl port-forward -n gitea svc/gitea-http "${LOCAL_PORT}:3000" >/dev/null 2>&1 &
PF_PID=$!
GITEA="http://127.0.0.1:${LOCAL_PORT}"
for _ in $(seq 1 30); do
    curl -fsS "${GITEA}/api/v1/version" >/dev/null 2>&1 && break
    sleep 2
done
curl -fsS "${GITEA}/api/v1/version" >/dev/null 2>&1 || die "Gitea is running but its API did not answer on the port-forward"

# --- 4. Create the org and repo, both public, and push ------------------------------------------
if [[ "${mode}" == "gitea" ]]; then
    log "[4/5] Creating ${GITEA_ORG}/${GITEA_REPO} and pushing your tree"
    curl -sS -u "${ADMIN_USER}:${ADMIN_PASS}" -X POST "${GITEA}/api/v1/orgs" \
        -H 'Content-Type: application/json' \
        -d "{\"username\":\"${GITEA_ORG}\",\"visibility\":\"public\"}" -o /dev/null || true
    curl -sS -u "${ADMIN_USER}:${ADMIN_PASS}" -X POST "${GITEA}/api/v1/orgs/${GITEA_ORG}/repos" \
        -H 'Content-Type: application/json' \
        -d "{\"name\":\"${GITEA_REPO}\",\"private\":false,\"auto_init\":false}" -o /dev/null || true

    REMOTE="http://${ADMIN_USER}:${ADMIN_PASS}@127.0.0.1:${LOCAL_PORT}/${GITEA_ORG}/${GITEA_REPO}.git"
    git -C "${REPO_ROOT}" remote remove cluster 2>/dev/null || true
    git -C "${REPO_ROOT}" remote add cluster "${REMOTE}"
    git -C "${REPO_ROOT}" push --quiet cluster HEAD:refs/heads/main --force
else
    log "[4/5] GitHub mode: ArgoCD reads $(sed -n 's/^ *repoURL: *//p' "${ROOT_APP}" | head -1)"
    log "      Make sure your latest commit is pushed there."
fi

# --- 5. Hand ArgoCD the root App-of-Apps --------------------------------------------------------
log "[5/5] Applying the foundation App-of-Apps"
kubectl apply -n argocd -f "${ROOT_APP}"

cat <<EOF

ArgoCD is reconciling the foundation from ${mode}.

Watch it converge:
    kubectl get applications -n argocd -w

After every commit:
    ./provision/push-to-cluster.sh

Your local clone is the source of truth. The copy inside the cluster dies with the cluster.
EOF
