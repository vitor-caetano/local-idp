#!/usr/bin/env bash
# ABOUTME: Brings the cluster back after a laptop or Docker VM restart: raises the inotify limits the
# ABOUTME: restart reset, restarts the pods that crash-looped, and refills the in-memory OpenBao.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

require_tools docker kind kubectl

kind get clusters 2>/dev/null | grep -qx "${CLUSTER_NAME}" \
    || die "Kind cluster ${CLUSTER_NAME} does not exist; run ./provision/create-cluster.sh"
guard_context

# --- 1. The limits the VM restart reset ---------------------------------------------------------
log "[1/4] Checking inotify limits"
raise_inotify_limits

# --- 2. kube-proxy first ------------------------------------------------------------------------
# Every other crash depends on it: a node without kube-proxy cannot reach any Service IP, the API
# server included. Deleting a pod skips the CrashLoopBackOff wait; its DaemonSet recreates it.
log "[2/4] Restarting kube-proxy pods that are not ready"
kubectl wait --for=condition=Ready nodes --all --timeout=180s >/dev/null
kubectl -n kube-system get pods -l k8s-app=kube-proxy \
    -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.status.containerStatuses[0].ready}{"\n"}{end}' \
    | while read -r pod ready; do
        [[ "${ready}" == "true" ]] && continue
        log "  kube-system/${pod}"
        kubectl -n kube-system delete pod "${pod}" --wait=false >/dev/null
    done
kubectl -n kube-system rollout status daemonset/kube-proxy --timeout=180s >/dev/null

# --- 3. Everything that crash-looped while Service routing was down ------------------------------
# These recover by themselves once the backoff expires, up to five minutes each. Restarting them now
# is faster. Every one is owned by a controller, so deleting it only replaces it.
log "[3/4] Restarting pods stuck in CrashLoopBackOff"
restarted=0
while read -r ns pod reasons; do
    [[ "${reasons}" == *CrashLoopBackOff* ]] || continue
    log "  ${ns}/${pod}"
    kubectl -n "${ns}" delete pod "${pod}" --wait=false >/dev/null
    restarted=$((restarted + 1))
done < <(kubectl get pods -A \
    -o jsonpath='{range .items[*]}{.metadata.namespace}{" "}{.metadata.name}{" "}{.status.containerStatuses[*].state.waiting.reason}{"\n"}{end}')
log "Restarted ${restarted} pod(s)"

# --- 4. Refill OpenBao --------------------------------------------------------------------------
# OpenBao runs in dev mode, in memory, so the restart emptied it. The Secrets External Secrets wrote
# before the restart survive, and Postgres only read its password when its data directory was first
# initialised. So the Backstage Postgres credentials go back from the surviving Secret: re-running
# the seed Job first would generate a new password Postgres does not know.
log "[4/4] Refilling OpenBao if the restart emptied it"
kubectl -n openbao wait --for=condition=Ready pod/openbao-0 --timeout=180s >/dev/null
bao_token="$(kubectl -n openbao get secret openbao-root-token -o jsonpath='{.data.token}' | base64 --decode)"
if kubectl -n openbao exec openbao-0 -- env BAO_TOKEN="${bao_token}" \
        bao kv get secret/backstage-postgres >/dev/null 2>&1; then
    log "  OpenBao still holds secret/backstage-postgres, nothing to refill"
else
    pg_secret="$(kubectl -n backstage get secret backstage-postgres \
        -o jsonpath='{.data.POSTGRES_USER} {.data.POSTGRES_PASSWORD}' 2>/dev/null || true)"
    [[ -n "${pg_secret// /}" ]] \
        || die "OpenBao is empty and backstage/backstage-postgres is gone; the Postgres password is lost"
    read -r pg_user_b64 pg_password_b64 <<<"${pg_secret}"
    # The password travels on stdin (password=-), so it never appears in a process list or a log.
    base64 --decode <<<"${pg_password_b64}" \
        | kubectl -n openbao exec -i openbao-0 -- env BAO_TOKEN="${bao_token}" \
            bao kv put secret/backstage-postgres \
                username="$(base64 --decode <<<"${pg_user_b64}")" password=- >/dev/null
    log "  restored secret/backstage-postgres from backstage/backstage-postgres"

    # The seed Job owns every other value. Deleting it makes ArgoCD recreate it, and it leaves the
    # Postgres credentials alone now that they are present.
    kubectl -n openbao delete job openbao-seed --ignore-not-found >/dev/null
    log "  deleted job openbao-seed; ArgoCD recreates it and it re-seeds the rest"
    for _ in $(seq 36); do
        kubectl -n openbao get job openbao-seed >/dev/null 2>&1 && break
        sleep 5
    done
    kubectl -n openbao get job openbao-seed >/dev/null 2>&1 \
        || die "ArgoCD did not recreate job openbao-seed within 3 minutes; sync openbao-config"
    kubectl -n openbao wait --for=condition=Complete job/openbao-seed --timeout=180s >/dev/null
fi

# External Secrets retries a failed sync with a backoff that grows past the time this script should
# take, so ask it to sync now. A changed force-sync annotation is its documented trigger.
kubectl annotate externalsecret --all -A force-sync="$(date +%s)" --overwrite >/dev/null
kubectl wait --for=condition=Ready externalsecret --all -A --timeout=300s >/dev/null
log "Every ExternalSecret is Ready. Watch pods settle with: kubectl get pods -A | grep -v Running"
