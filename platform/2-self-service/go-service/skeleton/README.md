# ${{ values.name }}

${{ values.description }}

Scaffolded from the platform's Go service golden path.

## How it ships

Every push to `main` runs the platform CI pipeline: `go vet`, `go test`, an image build, and a
commit that sets the new image tag in `manifests/kustomization.yaml`. ArgoCD deploys that commit as
a canary Rollout. The tag commit carries `[skip ci]`, so it does not trigger another build.

| | |
|---|---|
| Service | https://${{ values.name }}.localtest.me |
| CI runs | https://workflows.localtest.me/workflows/ci |
| Deployment | https://argocd.localtest.me/applications/argocd/svc-${{ values.name }} |

## Endpoints

- `/` returns a greeting
- `/healthz` is the liveness and readiness probe
- `/metrics` exposes `http_requests_total` for Prometheus, which KEDA scales on

## Run it locally

```bash
go test ./...
go run .
curl localhost:8080/
```
