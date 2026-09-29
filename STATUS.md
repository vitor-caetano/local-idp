# Status

Where the build stands. Update this file when a phase completes.

## As of 2026-09-29

**Scaffolded, not built.** Every file exists and the cluster-free suite passes (`uv run --group test
pytest`). No cluster has been created, nothing has been applied, and the repo has no remote yet.

| Phase | State |
|---|---|
| 0 Preflight and cluster | Not started |
| 1 to 7 | Not started |

## Next steps

1. Resize the Rancher Desktop VM to 16 GB memory and 6 CPUs, with the dockerd (moby) engine. It
   was about 6 GB and 2 CPUs, and `provision/create-cluster.sh` refuses to run below 14 GiB and 6.
2. Raise the inotify limits (see `docs/prerequisites.md`).
3. Start phase 0: `spec/phases/phase-0-preflight.md`, with the prompt in `prompts/prompt-library.md`.

## Unproven until the first build

These were resolved from upstream on 2026-09-29 and have never run on this platform. If one fails,
fix the pin in `components.yaml` and the Application, then run `scripts/gen-versions-lock.py`.

| Item | Where it bites |
|---|---|
| Kind v0.33.0 with node image v1.36.4 | Phase 0 |
| The containerd `config_path` patch in `provision/kind-config.yaml` (older key format) | Phase 0; `create-cluster.sh` fails loudly if it did not take |
| Envoy Gateway 1.9.2, and the EnvoyProxy NodePort patch | Phase 1 |
| Grafana Alloy chart 1.13.0 and its config | Phase 3 |
| Argo Workflows chart 1.0.16 values keys (`workflowNamespaces`, `workflow.serviceAccount`) | Phase 4 |
| BuildKit v0.33.0 rootless | Phase 6 |
| The Sensor's `comparator: "!="` on a string filter, and the Gitea push payload keys | Phase 6 |

Components shared with the EKS sibling platform (ArgoCD, Gitea, cert-manager, OpenBao, ESO,
Kyverno, the observability charts, the Argo charts, KEDA, Backstage) reuse pins that build validated.

## Known open items

- The Backstage ArgoCD and Kubernetes tabs are installed but not wired into the entity page. See
  `images/backstage/README.md`.
- No GitHub remote yet. Add one before trying `set-git-source.sh github`.
