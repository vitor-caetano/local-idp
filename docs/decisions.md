# Decisions

Dated log of how the architecture was reached. Newest last. A decision is superseded by a later
entry, never edited in place.

## D1, 2026-09-29: Kind instead of EKS

The sibling platform runs on EKS. This one exists to run the same foundation at no cost on one
machine, so it drops the cloud provider. Kind over k3d and minikube: multi-node from a config file,
and a documented local-registry pattern.

## D2, 2026-09-29: No AI plane

kgateway, agentgateway, kagent, KServe, vLLM, llm-d and LLM Guard are out. What remains is the
foundation and self-service planes, which are useful without any AI component.

## D3, 2026-09-29: Envoy Gateway for Gateway API

ingress-nginx is end of life. On EKS the AWS Load Balancer Controller fronted the cluster; on Kind
nothing does, so the Gateway API implementation also has to be the edge. Envoy Gateway ships the
Gateway API CRDs, and its EnvoyProxy resource can pin the data plane to fixed NodePorts.

## D4, 2026-09-29: Two Git sources, one switch

The in-cluster Gitea keeps the build offline and self-contained. GitHub is useful to experiment with
a remote source. Both are supported through placeholders that `set-git-source.sh` rewrites, rather
than two copies of the manifests. Gitea stays installed in GitHub mode because the golden-path
service repos and their webhooks live there.

## D5, 2026-09-29: Charts from upstream, not vendored

Vendoring made the EKS build immune to network hiccups during a timed live session. A laptop build
has no such constraint, and vendored tarballs cost repo size and a vendoring script. Charts are
pulled at the pinned version from upstream.

## D6, 2026-09-29: A Go service golden path with in-cluster CI

The sibling platform's golden path scaffolds an AI agent. This one scaffolds a Go HTTP service and
builds it in the cluster, so the path exercises Argo Events, Argo Workflows, the registry, Rollouts
and KEDA end to end. The service uses only the standard library, so there is no `go.sum` for the
template to keep current.

## D7, 2026-09-29: Rootless BuildKit over Kaniko

The original Kaniko project is archived. Rootless BuildKit is maintained, needs no Docker socket, and
runs as uid 1000. Its cost is seccomp and AppArmor Unconfined, which confines it to the privileged
`ci` namespace.

## D8, 2026-09-29: Postgres for Backstage from a plain StatefulSet

The Backstage chart's bundled PostgreSQL is Bitnami's, whose images moved behind a paid tier. One
Postgres pod needs nothing a chart adds, and a plain StatefulSet makes its ExternalSecret-sourced
password easy to follow.

## D9, 2026-09-29: Application health drives the sync waves

ArgoCD stopped assessing child Application health in 1.8, which reduces sync waves in an App-of-Apps
to creation order. The health check is restored in `argocd-values.yaml`, so a wave waits for the one
before it. The trade: a stuck early wave holds everything after it, which points straight at the
problem.
