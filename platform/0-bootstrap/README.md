# Bootstrap

How the cluster goes from empty to reconciling the platform from Git.

## 1. Install ArgoCD (the one allowed direct install)

```bash
./provision/bootstrap-argocd.sh
```

It runs `helm upgrade --install` for the `argo-cd` chart at the version pinned in
`components.yaml`, with `argocd-values.yaml` from this directory. The values turn on
`server.insecure` (TLS terminates at the Gateway), create the read-only `backstage` account, and add
health checks for the Gateway API and Argo Events kinds ArgoCD cannot assess on its own.

## 2. Seed the Git host and apply the foundation

```bash
./provision/seed-gitea.sh
```

Gitea's own Application pulls its chart from `dl.gitea.com`, so it is the one Application that can
be applied before a Git host exists. The script applies it, waits for Gitea, creates
`platform/local-idp`, pushes your tree, and applies `root-app.yaml`.

## 3. The plane roots

| File | Application | Applied |
|---|---|---|
| `root-app.yaml` | `platform-foundation` | by `seed-gitea.sh`, phase 1 |
| `self-service-app.yaml` | `platform-self-service` | by hand at the start of phase 6 |

Each recurses its plane directory for `*/application.yaml`. Both carry `REPLACE_WITH_PLATFORM_REPO_URL`
in the reference build; `provision/set-git-source.sh` fills it in your working copy.

## Sync waves in the foundation

| Wave | Components |
|---|---|
| 0 | platform-namespaces, cert-manager, envoy-gateway, gitea |
| 1 | cert-manager-issuers, openbao, external-secrets, kyverno |
| 2 | platform-gateway, openbao-config, kube-prometheus-stack, loki, tempo |
| 3 | alloy, opentelemetry-collector, gitea-config, argo-workflows, argo-events, argo-rollouts, keda |
| 4 | backstage-config |
| 5 | backstage |
| 6 | platform-routes, policy-baseline |

The `argoproj.io_Application` health check in `argocd-values.yaml` is what makes each wave wait for
the previous one to be Healthy. Without it, waves only order creation. Waves matter for the first
sync only; after that, every Application reconciles on its own.
