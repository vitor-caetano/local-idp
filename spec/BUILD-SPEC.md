# Platform Build Spec

This is the spec your agentic CLI ingests. It drives the build of a GitOps Internal Developer
Platform on a local Kind cluster, phase by phase, and each phase has a test in `tests/` that proves
it landed.

For the reasoning behind a choice, read `docs/architecture.md` and `docs/decisions.md`. This file is
the one you and your agent actually run.

## What you are building

An IDP on a three-node Kind cluster: ArgoCD reconciling from Git, Envoy Gateway serving every UI at
`https://<name>.localtest.me`, secrets from OpenBao through External Secrets, Kyverno policy, the
Prometheus, Loki, Tempo and OpenTelemetry observability plane, the Argo Workflows, Events and
Rollouts stack with KEDA, Backstage, and a golden path that scaffolds a Go service, builds it in the
cluster, and deploys it as a canary.

## Starting state

Docker (Rancher Desktop, dockerd engine) with at least 14 GiB and 6 CPUs, and the tools in
`docs/prerequisites.md`. No cluster yet. `provision/create-cluster.sh` creates it in phase 0.

## Non-negotiable rules

1. **One phase at a time, and stop at the end of each.** Do not start the next phase until the user
   confirms.
2. **Test first.** For each phase, write or read the phase test, run it to confirm it fails, build,
   then run it to confirm it passes. No mocks, no stubs.
3. **Everything after the bootstrap flows through Git and ArgoCD.** The only direct installs are
   ArgoCD itself, the Gitea seed, and the phase 7 denial demo. Use server-side apply for CRDs.
4. **Pin every version.** Use `components.yaml`. Do not invent versions.
5. **Cluster context safety.** Every command uses `KUBECONFIG=$HOME/.kube/local-idp`, and every
   mutating command first confirms the context is `kind-local-idp`.
6. **No secrets in Git** beyond the documented local dev values (Gitea admin, OpenBao root token,
   Grafana admin).

## Build rules: avoid these known failures

1. **Per-cluster values are placeholders, substituted by a script.** Every Git-sourced Application
   reads `REPLACE_WITH_PLATFORM_REPO_URL`; `provision/set-git-source.sh` fills it.
2. **`runAsNonRoot: true` always pairs with a numeric `runAsUser`.** Find the image's uid with `id`.
3. **An image `repository` must not repeat the registry host.**
4. **The runtime user must be able to traverse its working directory.**
5. **Read shared credentials from one Secret.** Never a second hardcoded copy.
6. **Install first, enforce last.** Every Kyverno policy ships `failureAction: Audit`. The one flip
   to Enforce is the golden-path set, in phase 7.
7. **Every custom resource the platform waits on has an ArgoCD health check**, or ArgoCD reports it
   Healthy regardless.
8. **Validate before you commit.** `helm template` the chart with your values, round-trip the YAML,
   and run the cluster-free suite.

When something does not converge, diagnose from ArgoCD status and pod events, fix the root cause in
Git, commit, and push. Deleting a pod does not fix a Git-sourced fault.

## Completion gate per phase

A phase is done when its test passes and its files are committed. Output the completion promise,
then stop.

## Phases

| Phase | Name | What it delivers |
|---|---|---|
| 0 | Preflight and cluster | Tools, VM size, the registry, the Kind cluster, registry reachability from pods |
| 1 | GitOps and traffic | ArgoCD, Gitea, cert-manager with the local CA, Envoy Gateway, the platform Gateway, the Git source switch |
| 2 | Secrets and policy | OpenBao, External Secrets, Kyverno, the Audit baseline |
| 3 | Observability | kube-prometheus-stack, Loki with Alloy, Tempo, the OpenTelemetry Collector |
| 4 | Delivery and automation | Argo Workflows, Argo Events, Argo Rollouts, KEDA |
| 5 | Developer portal | Backstage image, Postgres from OpenBao, Backstage, every UI routed |
| 6 | Golden path | The Go service template, CI pipeline, deploy ApplicationSet, golden-path policies in Audit |
| 7 | Governance | Flip the golden-path policies to Enforce, and the denial demo |

Each phase has a file in `spec/phases/` with its goal, outputs, test criteria, completion promise
and stop.

## How to run this

1. Read this file and `components.yaml`.
2. Start at phase 0.
3. For each phase: read the phase file, run its test and see it fail, build, see it pass, commit,
   output the promise, stop.
