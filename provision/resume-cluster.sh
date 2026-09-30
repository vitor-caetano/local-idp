#!/usr/bin/env bash
# ABOUTME: Brings the cluster back after a laptop or Docker VM restart: raises the inotify limits the
# ABOUTME: restart reset, then restarts every pod that crash-looped while they were low.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

require_tools docker kind kubectl

kind get clusters 2>/dev/null | grep -qx "${CLUSTER_NAME}" \
    || die "Kind cluster ${CLUSTER_NAME} does not exist; run ./provision/create-cluster.sh"
guard_context

# --- 1. The limits the VM restart reset ---------------------------------------------------------
log "[1/3] Checking inotify limits"
raise_inotify_limits

# --- 2. kube-proxy first ------------------------------------------------------------------------
# Every other crash depends on it: a node without kube-proxy cannot reach any Service IP, the API
# server included. Deleting a pod skips the CrashLoopBackOff wait; its DaemonSet recreates it.
log "[2/3] Restarting kube-proxy pods that are not ready"
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
log "[3/3] Restarting pods stuck in CrashLoopBackOff"
restarted=0
while read -r ns pod reasons; do
    [[ "${reasons}" == *CrashLoopBackOff* ]] || continue
    log "  ${ns}/${pod}"
    kubectl -n "${ns}" delete pod "${pod}" --wait=false >/dev/null
    restarted=$((restarted + 1))
done < <(kubectl get pods -A \
    -o jsonpath='{range .items[*]}{.metadata.namespace}{" "}{.metadata.name}{" "}{.status.containerStatuses[*].state.waiting.reason}{"\n"}{end}')
log "Restarted ${restarted} pod(s). Watch them settle with: kubectl get pods -A | grep -v Running"
