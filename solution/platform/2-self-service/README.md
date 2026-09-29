# 2-self-service: the golden path

Applied by `../0-bootstrap/self-service-app.yaml` at the start of phase 6.

| Directory | Wave | What it is |
|---|---|---|
| `ci-pipeline/` | 0 | JetStream EventBus, the Gitea webhook EventSource, the Sensor that submits CI, and the `ci-go-service` WorkflowTemplate |
| `golden-path-deploy/` | 1 | The `golden-path-services` AppProject and the ApplicationSet that deploys every repo in the Gitea `services` org |
| `golden-path-policies/` | 2 | Kyverno rules for golden-path workloads. Audit until phase 7 flips them to Enforce |
| `go-service/` | none | The Backstage template and its skeleton. Read by Backstage, never applied to the cluster |
| `catalog/` | none | The Backstage org file (the `platform-team` group) |

## The loop

1. Backstage runs the `go-service` template. It renders the skeleton and publishes a public repo to
   `services/<name>` in Gitea, then registers `catalog-info.yaml` in the catalog.
2. The push fires the org webhook that gitea-config created. The `gitea` EventSource receives it and
   the `ci-go-service` Sensor submits a Workflow in `ci`.
3. The Workflow clones the commit, runs `go vet` and `go test`, builds the image with rootless
   BuildKit, pushes `kind-registry:5000/services/<name>:<sha>`, then commits the new tag into
   `manifests/kustomization.yaml` with `[skip ci]` in the message.
4. The ApplicationSet has already generated `svc-<name>` for the repo. ArgoCD sees the tag commit and
   syncs; the Rollout canaries the new pods in.
5. The service answers at `https://<name>.localtest.me`, Prometheus scrapes its `/metrics`, and KEDA
   scales it on request rate.

The first sync, before CI has pushed an image, points at the tag `initial`, which does not exist.
The Rollout shows `ImagePullBackOff` for the minute it takes the first build to finish.
