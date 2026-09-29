# 1-foundation: the foundation plane

One directory per component. Each holds an ArgoCD `application.yaml`, plus any raw manifests under
`manifests/`, which that component's own Application owns. The root App-of-Apps at
`../0-bootstrap/root-app.yaml` picks up only the `application.yaml` files.

Helm-sourced components pull their charts from upstream at the version pinned in
`components.yaml`. Manifest-sourced components read from `REPLACE_WITH_PLATFORM_REPO_URL`, which
`provision/set-git-source.sh` fills in your working copy.

| Component | Wave | Source | What it is for |
|---|---|---|---|
| platform-namespaces | 0 | manifests | Shared namespaces and their labels: `platform-gateway`, `backstage`, `ci`, `apps` |
| cert-manager | 0 | chart | Certificates |
| envoy-gateway | 0 | chart | Gateway API controller and CRDs |
| gitea | 0 | chart | The in-cluster Git host |
| cert-manager-issuers | 1 | manifests | Self-signed root CA and the `local-idp-ca` ClusterIssuer |
| openbao | 1 | chart | Secret backend, dev mode |
| external-secrets | 1 | chart | Pulls OpenBao secrets into Kubernetes Secrets |
| kyverno | 1 | chart | Admission policy engine |
| platform-gateway | 2 | manifests | GatewayClass, NodePort EnvoyProxy, the `platform-gateway` Gateway, wildcard cert, HTTP to HTTPS redirect |
| openbao-config | 2 | manifests | ClusterSecretStore, seed Job, demo ExternalSecret |
| kube-prometheus-stack | 2 | chart | Prometheus, Alertmanager, Grafana |
| loki | 2 | chart | Logs |
| tempo | 2 | chart | Traces |
| alloy | 3 | chart | Ships pod logs to Loki |
| opentelemetry-collector | 3 | chart | OTLP in, Tempo out |
| gitea-config | 3 | manifests | Seeds the `services` org, tokens, the CI webhook, and Backstage's integration Secret |
| argo-workflows | 3 | chart | Runs the CI pipeline in `ci` |
| argo-events | 3 | chart | Turns Gitea pushes into Workflows |
| argo-rollouts | 3 | chart | Canary delivery for golden-path services |
| keda | 3 | chart | Scales golden-path services on Prometheus queries |
| backstage-config | 4 | manifests | Backstage's Postgres, its ExternalSecret, and the Kubernetes plugin's read-only RBAC |
| backstage | 5 | chart | The portal |
| platform-routes | 6 | manifests | HTTPRoutes for every UI at `*.localtest.me` |
| policy-baseline | 6 | manifests | Kyverno baseline for `apps`, Audit forever |
