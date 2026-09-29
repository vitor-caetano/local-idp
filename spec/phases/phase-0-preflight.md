# Phase 0: Preflight and cluster

**Goal:** A three-node Kind cluster with a working local registry, and proof that the machine is big
enough for the rest of the build.

**Inputs:** Docker (Rancher Desktop, dockerd engine), and the tools in `docs/prerequisites.md`.

**Outputs:**
- The `kind-registry` container on `127.0.0.1:5001`, attached to the `kind` network
- The Kind cluster `local-idp`: one control plane with host ports 80 and 443, two workers,
  Kubernetes 1.36 from the pinned node image
- Kubeconfig at `~/.kube/local-idp`, context `kind-local-idp`
- containerd on every node mapping `localhost:5001` to `http://kind-registry:5000`
- A short note of what the cluster contains (it should be close to empty)

**How:** `./provision/create-cluster.sh`. It refuses to run on a VM with less than 14 GiB or 6 CPUs.

**Test criteria (`tests/test_phase_0_preflight.py`):**
- `components.yaml` parses and every entry is pinned (cluster-free)
- Three nodes, all Ready, one of them labelled `ingress-ready=true`
- Server version is 1.36
- The `argocd` namespace does not exist yet
- A pod can pull an image pushed to `localhost:5001` (the test pushes a tiny one first)
- A pod can resolve and reach `kind-registry:5000`, which the CI build pushes to in phase 6

**Completion promise:** `<promise>PHASE0_DONE</promise>`

**Key decisions:**
- Kind over k3d or minikube: multi-node, config as a file, and the documented local-registry pattern.
- The registry is a container outside the cluster, so images survive `destroy.sh --keep-registry`.
- Do not install anything into the cluster in this phase.

**Stop here.** The cluster is bare. From the next phase on, your agent builds the platform.
