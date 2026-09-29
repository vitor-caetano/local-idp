# versions.lock.md

Pinned chart and image versions for the platform. `components.yaml` is the machine-readable source
of truth; this file is the quick lookup. The table below is generated: run
`python3 scripts/gen-versions-lock.py` after changing `components.yaml`, and
`python3 scripts/gen-versions-lock.py --check` fails when the two disagree.

| Component | App version | Chart | Chart version | Chart repo |
|---|---|---|---|---|
| Kind | v0.33.0 | n/a (cli) | n/a | n/a |
| Kind node image | v1.36.4@sha256:099e049362a1526b2db71494e1947aae99bd16290d7c895f2b7ea312e3cbfaed | n/a (image) | n/a | n/a |
| Local image registry | registry:3.1.2 | n/a (image) | n/a | n/a |
| Argo CD | v3.4.4 | argo-cd | 9.5.22 | argoproj.github.io/argo-helm |
| Gitea | 1.26.1 | gitea | 12.6.0 | dl.gitea.com/charts/ |
| cert-manager | v1.20.2 | cert-manager | v1.20.2 | charts.jetstack.io |
| Envoy Gateway | v1.9.2 | gateway-helm | 1.9.2 | oci://docker.io/envoyproxy |
| OpenBao | v2.5.5 | openbao | 0.28.4 | openbao.github.io/openbao-helm |
| External Secrets Operator | v2.6.0 | external-secrets | 2.6.0 | charts.external-secrets.io |
| Kyverno | v1.18.1 | kyverno | 3.8.1 | kyverno.github.io/kyverno |
| kube-prometheus-stack | operator v0.91.0 | kube-prometheus-stack | 86.3.2 | prometheus-community.github.io/helm-charts |
| Loki | 3.7.2 | loki | 17.4.7 | grafana-community.github.io/helm-charts |
| Grafana Alloy | v1.20.0 | alloy | 1.13.0 | grafana.github.io/helm-charts |
| Tempo | 2.9.0 | tempo | 1.25.0 | grafana-community.github.io/helm-charts |
| OTel Collector | 0.153.0 | opentelemetry-collector | 0.158.2 | open-telemetry.github.io/opentelemetry-helm-charts |
| Argo Workflows | v4.0.6 | argo-workflows | 1.0.16 | argoproj.github.io/argo-helm |
| Argo Events | v1.9.10 | argo-events | 2.4.22 | argoproj.github.io/argo-helm |
| Argo Rollouts | v1.9.0 | argo-rollouts | 2.41.0 | argoproj.github.io/argo-helm |
| KEDA | 2.20.1 | keda | 2.20.1 | kedacore.github.io/charts |
| Backstage | 1.51.2 | backstage | 2.8.2 | backstage.github.io/charts |
| PostgreSQL for Backstage | postgres:17.6 | n/a (kubectl) | n/a | n/a |
| BuildKit (rootless) | moby/buildkit:v0.33.0-rootless | n/a (image) | n/a | n/a |
| Go toolchain image | golang:1.27.0 | n/a (image) | n/a | n/a |
| Go service golden path | scaffolder.backstage.io/v1beta3 | n/a (kubectl) | n/a | n/a |

A bump is done when the phase suite passes against it, not when the number changes.
