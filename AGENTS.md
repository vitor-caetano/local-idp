# AGENTS.md

Project memory for this repository, written for two readers: the person building the platform, and
the coding agent they point at this tree.

An agent builds a GitOps Internal Developer Platform on a local Kind cluster from the spec in
`spec/`, one phase at a time, and `tests/` proves each phase landed. `solution/` is the finished
build, for when you want to compare rather than debug.

Start with `docs/prerequisites.md`, then `provision/README.md` for the cluster, then
`spec/BUILD-SPEC.md`. `docs/architecture.md` holds the settled decisions, `docs/decisions.md` the
dated log of how they were reached, and `docs/what-is-not-included.md` what was left out on purpose.

## Manifest defect classes. Check for each before believing a build is healthy.

Every one of these produces a component that reports Synced, reports Healthy, and does not work.

1. **An unsubstituted `REPLACE_WITH_*` placeholder.** `grep -rn --include="*.yaml" REPLACE_WITH platform/` must return
   nothing once `provision/set-git-source.sh` has run. The reference under `solution/` keeps its
   placeholders on purpose.
2. **`runAsNonRoot: true` with no numeric `runAsUser`** on an image whose USER is root or
   non-numeric. The kubelet refuses it with `CreateContainerConfigError`. Pin the uid the image
   actually uses; verify with `id` inside it rather than guessing.
3. **An image `repository` that repeats the registry host** (`registry: localhost:5001` plus
   `repository: localhost:5001/...`), producing a doubled path.
4. **A directory the container cannot traverse.** `Cannot find module '/app/...'` for a path that
   holds the module is a permission problem, not a missing build.
5. **Hardcoded credentials that drift.** Read shared credentials from one Secret, never a second
   copy in a Job manifest.
6. **A custom resource ArgoCD cannot assess.** ArgoCD reports Healthy for anything it has no health
   check for. `solution/platform/0-bootstrap/argocd-values.yaml` carries the checks and
   `tests/test_argocd_health_checks.py` fails if a new kind arrives unassessed.
7. **A route with no parent.** An HTTPRoute whose `parentRefs` names a Gateway, namespace or
   listener that does not exist sits `Accepted=False` while its Application reads green. The
   HTTPRoute health check in `argocd-values.yaml` turns that red.

`tests/test_platform_contract.py` asserts 1, 2, 3 and 5. Run the cluster-free suite after any
manifest change:

```bash
uv run --group test pytest
```

## What this repo is

A GitOps-driven Internal Developer Platform that runs on a laptop. ArgoCD reconciles everything from
Git. The platform is Backstage, the Argo stack, KEDA, the observability plane (Prometheus, Grafana,
Loki, Tempo, OpenTelemetry), policy and secrets tooling (Kyverno, OpenBao, External Secrets), and a
golden path that scaffolds a Go service, builds it in-cluster, and deploys it with a canary.

There is no AI plane and no cloud provider. It is the foundation and self-service planes of an IDP,
sized for Kind.

## Repo map

- `provision/` holds the Kind config and the scripts that create the cluster and local registry,
  install ArgoCD, seed Gitea, switch the Git source, and tear everything down.
- `components.yaml` is the single source of truth for the component set. Every entry is pinned.
- `versions.lock.md` is generated from `components.yaml` by `scripts/gen-versions-lock.py`.
- `solution/platform/0-bootstrap/` holds the ArgoCD values and one App-of-Apps per plane.
- `solution/platform/1-foundation/` holds one directory per foundation component.
- `solution/platform/2-self-service/` holds the golden path: template, CI pipeline, deploy
  ApplicationSet, and the policies that govern it.
- `platform/` is **your** working copy, the tree your agent builds and the one ArgoCD reads. It does
  not exist until you create it.
- `images/backstage/` builds the Backstage image and pushes it to the local registry.
- `spec/` holds the build spec and one file per phase; `prompts/` the prompts that drive them.

## Getting to a running platform

```bash
./provision/create-cluster.sh              # local registry + 3-node Kind cluster
export KUBECONFIG="$HOME/.kube/local-idp"
cp -a solution/platform/. platform/        # or let the agent generate platform/
./provision/set-git-source.sh gitea        # fills in the Git source placeholders
./provision/bootstrap-argocd.sh            # the one direct install
./images/backstage/build-and-push.sh       # Backstage image into localhost:5001
./provision/seed-gitea.sh                  # installs Gitea, pushes your tree, starts ArgoCD
```

Afterwards, `./provision/push-to-cluster.sh` sends each commit to the cluster. Tear down with
`./provision/destroy.sh`.

## Git source

ArgoCD can read the platform from the in-cluster Gitea or from GitHub.
`provision/set-git-source.sh gitea` or `provision/set-git-source.sh github <https-url>` rewrites
every platform `repoURL` in `platform/` and commits the change. Gitea is installed in both modes,
because the golden-path service repos and their CI webhooks always live there.

## GitOps rules

- Cluster context safety: every kubectl and helm command uses `KUBECONFIG=$HOME/.kube/local-idp`
  and never writes to `~/.kube/config`. Verify `kubectl config current-context` is
  `kind-local-idp` before any mutating command. Only touch clusters you created.
- All cluster changes flow through Git. ArgoCD applies them.
- Install first, enforce last. Every Kyverno policy ships with `failureAction: Audit`. The single
  sanctioned flip to Enforce is the golden-path policy set in phase 7. The foundation baseline
  stays Audit.
- Never run mutating `kubectl` directly against the cluster, except for the bootstrap (installing
  ArgoCD and seeding Gitea) and the scripted Kyverno denial demonstration.
- CRDs require server-side apply: `kubectl apply --server-side --force-conflicts`. Every
  Application sets `ServerSideApply=true`.
- ArgoCD is on the 3.x line. RBAC changed in 3.0: `update` and `delete` no longer cascade to
  managed sub-resources, and logs need explicit `logs, get` permission.

## Naming and namespaces

- Descriptive kebab-case everywhere. No `improved`, `new`, or `enhanced` in names.
- One namespace per logical area: `argocd`, `gitea`, `cert-manager`, `envoy-gateway-system`,
  `platform-gateway`, `openbao`, `external-secrets`, `kyverno`, `observability`, `argo`,
  `argo-events`, `argo-rollouts`, `keda`, `backstage`, `ci`, `apps`.
- Hostnames are `<name>.localtest.me`, which resolves to 127.0.0.1 without touching `/etc/hosts`.

## Platform facts that are easy to get wrong

- ingress-nginx is end of life. Ingress is Gateway API through Envoy Gateway. Kind has no load
  balancer, so the Envoy Service is a NodePort on 30080 and 30443, and the Kind config maps host
  ports 80 and 443 onto those.
- Storage is Kind's built-in `local-path` provisioner, StorageClass `standard`. Volumes are bound to
  the node that first used them.
- Images you build go to the registry container `kind-registry`. From your Mac and from node
  containerd it is `localhost:5001`; from inside a pod (the CI build pushing) it is
  `kind-registry:5000`. Manifests reference `localhost:5001/...`.
- ArgoCD serves plain HTTP inside the cluster (`server.insecure`), and TLS terminates at the Gateway
  with a certificate from the local CA.
- Kind has no metrics-server, so KEDA scales on Prometheus queries, not CPU.
- Gitea blocks webhooks to private addresses by default. `webhook.ALLOWED_HOST_LIST: private` is
  what lets it reach the Argo Events webhook in the cluster.
- The CI pipeline commits the new image tag back to the service repo. The Sensor ignores commits
  whose message contains `[skip ci]`, which is what stops that commit from building itself forever.

## Testing

Cluster-free tests run anywhere. Cluster-bound tests skip themselves unless `KUBECONFIG_FILE` and
`EXPECTED_CONTEXT` are set, so a bare `pytest` is safe with no cluster. Nothing reads the default
kubeconfig, on purpose.

```bash
uv run --group test pytest
KUBECONFIG_FILE=$HOME/.kube/local-idp EXPECTED_CONTEXT=kind-local-idp \
  uv run --group test pytest tests/test_phase_1_foundation.py
```

## Writing standards for any doc generated here

- No em-dashes, no en-dashes. Commas, colons, periods.
- Banned words: delve, leverage, robust, seamless, comprehensive, under the hood, navigate
  complexities, genuinely, in today's landscape.
- No "it's not X, it's Y" inversions. No triadic lists as a default. No mirrored closing sentences.
- Direct and declarative. State things plainly. No hedging filler.

## Secrets

The repo contains zero real credentials. OpenBao (dev mode) is the in-cluster secret backend and
External Secrets Operator pulls from it. The dev passwords that appear in manifests (Gitea admin,
OpenBao root token, Grafana admin) are ephemeral and local to your own cluster.
