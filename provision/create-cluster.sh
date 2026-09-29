#!/usr/bin/env bash
# ABOUTME: Creates the local registry container and the three-node Kind cluster, and wires the two
# ABOUTME: together so nodes pull localhost:5001 images from the registry. Idempotent.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

require_tools docker kind kubectl

# --- 0. The Docker VM has to be big enough ------------------------------------------------------
# The full platform needs roughly 12 GB. On a smaller VM the later phases do not fail cleanly: pods
# sit Pending or get OOMKilled and ArgoCD reports Progressing forever.
mem_bytes="$(docker info --format '{{.MemTotal}}')"
cpus="$(docker info --format '{{.NCPU}}')"
mem_gib=$(( mem_bytes / 1024 / 1024 / 1024 ))
if (( mem_gib < 14 || cpus < 6 )); then
    die "the Docker VM has ${mem_gib} GiB and ${cpus} CPUs; the platform needs at least 14 GiB and 6 CPUs.
       Rancher Desktop: Preferences > Virtual Machine, set Memory 16 GB and CPUs 6, then re-run."
fi
log "Docker VM: ${mem_gib} GiB, ${cpus} CPUs"

# --- 1. The registry container ------------------------------------------------------------------
if [[ "$(docker inspect -f '{{.State.Running}}' "${REGISTRY_NAME}" 2>/dev/null || true)" != "true" ]]; then
    log "[1/5] Starting ${REGISTRY_NAME} on 127.0.0.1:${REGISTRY_PORT}"
    docker rm -f "${REGISTRY_NAME}" >/dev/null 2>&1 || true
    docker run -d --restart=always \
        -p "127.0.0.1:${REGISTRY_PORT}:5000" \
        --network bridge \
        --name "${REGISTRY_NAME}" \
        "${REGISTRY_IMAGE}" >/dev/null
else
    log "[1/5] ${REGISTRY_NAME} already running"
fi

# --- 2. The cluster ---------------------------------------------------------------------------
if kind get clusters 2>/dev/null | grep -qx "${CLUSTER_NAME}"; then
    log "[2/5] Kind cluster ${CLUSTER_NAME} already exists"
else
    log "[2/5] Creating Kind cluster ${CLUSTER_NAME} (kubeconfig ${KUBECONFIG})"
    mkdir -p "$(dirname "${KUBECONFIG}")"
    kind create cluster --config "${REPO_ROOT}/provision/kind-config.yaml" --kubeconfig "${KUBECONFIG}"
fi
guard_context

# --- 3. Point every node's containerd at the registry -------------------------------------------
log "[3/5] Mapping localhost:${REGISTRY_PORT} to http://${REGISTRY_NAME}:5000 on every node"
registry_dir="/etc/containerd/certs.d/localhost:${REGISTRY_PORT}"
for node in $(kind get nodes --name "${CLUSTER_NAME}"); do
    docker exec "${node}" mkdir -p "${registry_dir}"
    printf '[host."http://%s:5000"]\n' "${REGISTRY_NAME}" \
        | docker exec -i "${node}" cp /dev/stdin "${registry_dir}/hosts.toml"
    # The patch in kind-config.yaml must have landed, or the hosts.toml above is ignored and every
    # localhost:5001 pull fails with a connection refused that looks like a registry problem.
    if ! docker exec "${node}" grep -q 'certs.d' /etc/containerd/config.toml; then
        die "${node}: containerd config_path is not /etc/containerd/certs.d; check containerdConfigPatches"
    fi
done

# --- 4. Put the registry on the kind network ----------------------------------------------------
# This is what makes kind-registry resolvable from the nodes and from pods (the CI build pushes to
# kind-registry:5000).
if [[ "$(docker inspect -f '{{json .NetworkSettings.Networks.kind}}' "${REGISTRY_NAME}")" == "null" ]]; then
    log "[4/5] Connecting ${REGISTRY_NAME} to the kind network"
    docker network connect kind "${REGISTRY_NAME}"
else
    log "[4/5] ${REGISTRY_NAME} already on the kind network"
fi

# --- 5. Advertise the registry (KEP-1755) and check inotify limits -------------------------------
log "[5/5] Publishing the local-registry-hosting ConfigMap"
kubectl apply -f - >/dev/null <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: local-registry-hosting
  namespace: kube-public
data:
  localRegistryHosting.v1: |
    host: "localhost:${REGISTRY_PORT}"
    help: "https://kind.sigs.k8s.io/docs/user/local-registry/"
EOF

# Many controllers on one kernel exhaust the default inotify instances, and pods then crash with
# "too many open files". The limit belongs to the VM kernel, so check it from a node.
node="$(kind get nodes --name "${CLUSTER_NAME}" | head -1)"
instances="$(docker exec "${node}" cat /proc/sys/fs/inotify/max_user_instances)"
if (( instances < 512 )); then
    log "WARNING: fs.inotify.max_user_instances is ${instances}. Raise it before phase 3:"
    log "  rdctl shell sudo sysctl -w fs.inotify.max_user_instances=512 fs.inotify.max_user_watches=524288"
fi

cat <<EOF

Cluster ready. Use it with:
    export KUBECONFIG=${KUBECONFIG}
    kubectl get nodes

Next: cp -a solution/platform/. platform/  (or have your agent build platform/), then
      ./provision/set-git-source.sh gitea
EOF
