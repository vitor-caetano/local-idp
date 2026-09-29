# local-idp

A GitOps Internal Developer Platform that runs on a laptop, built by a coding agent from a written
spec, one phase at a time, with a test that proves each phase landed.

It is the foundation and self-service planes of a full IDP, sized for a three-node Kind cluster:

- **GitOps:** ArgoCD reconciling from an in-cluster Gitea, or from GitHub, switchable with one script
- **Traffic:** Gateway API through Envoy Gateway, every UI at `https://<name>.localtest.me` with a
  local CA
- **Secrets and policy:** OpenBao, External Secrets, Kyverno
- **Observability:** Prometheus, Grafana, Loki with Alloy, Tempo, the OpenTelemetry Collector
- **Delivery:** Argo Workflows, Argo Events, Argo Rollouts, KEDA
- **Portal:** Backstage, with a golden path that scaffolds a Go service, builds it in the cluster,
  and deploys it as a canary

No cloud account, no AI plane, no cost to run.

## Start here

0. `STATUS.md`: where the build stands and what to do next
1. `docs/prerequisites.md`: tools, and the Docker VM size (16 GB, 6 CPUs)
2. `provision/README.md`: creating and tearing down the cluster
3. `spec/BUILD-SPEC.md`: the build, phase by phase

`solution/platform/` is the finished build, for comparing against rather than copying blind.
`AGENTS.md` is the project memory your agent reads.

## The short version

```bash
./provision/create-cluster.sh
export KUBECONFIG="$HOME/.kube/local-idp"
cp -a solution/platform/. platform/
./provision/set-git-source.sh gitea
./provision/bootstrap-argocd.sh
PATH="$(brew --prefix node@24)/bin:$PATH" ./images/backstage/build-and-push.sh
./provision/seed-gitea.sh
./scripts/smoke-test.sh
```

Then apply `platform/0-bootstrap/self-service-app.yaml`, open https://backstage.localtest.me, and
create a service from the **Go service** template.

## Tests

```bash
uv run --group test pytest
```

Cluster-free by default. See `tests/README.md` for the phase gates.
