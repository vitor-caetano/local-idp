# Status

Where the build stands. Update this file when a phase completes.

## As of 2026-09-29

**Phase 0 done.** The Kind cluster `local-idp` runs three nodes on Kubernetes v1.36.4, with
`kind-registry` on `127.0.0.1:5001` attached to the `kind` network. `tests/test_phase_0_preflight.py`
passes (5 of 5). The cluster is bare: `default`, `kube-*` and `local-path-storage` namespaces only,
holding CoreDNS, kindnet, kube-proxy, the control plane, and the local-path provisioner. The repo is
public at https://github.com/vitor-caetano/local-idp.

| Phase | State |
|---|---|
| 0 Preflight and cluster | Done 2026-09-29 |
| 1 to 7 | Not started |

## Next steps

1. Install `yarn` and `node@24` before phase 1. The machine has Node 26 and no yarn, and the
   Backstage image build needs Node 24 (Node 25+ cannot build isolated-vm).
2. Start phase 1: `spec/phases/phase-1-gitops-and-traffic.md`.
3. The inotify limits reset when the Rancher Desktop VM restarts. Raise them again after each restart.

## Unproven until the first build

These were resolved from upstream on 2026-09-29 and have never run on this platform. If one fails,
fix the pin in `components.yaml` and the Application, then run `scripts/gen-versions-lock.py`.

| Item | Where it bites |
|---|---|
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
