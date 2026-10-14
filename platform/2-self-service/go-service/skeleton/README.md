# ${{ values.name }}

${{ values.description }}

Scaffolded from the local-idp golden path. Push to `main` and the platform does the rest:

1. Gitea's org webhook reaches the Argo Events EventSource, and the Sensor submits `ci-go-service`.
2. CI runs `go vet` and `go test`, builds the image with rootless BuildKit, pushes it to the local
   registry, and commits the new tag to `manifests/kustomization.yaml` with `[skip ci]`.
3. ArgoCD's `svc-${{ values.name }}` Application rolls the new tag out as a canary.

It answers at https://${{ values.name }}.localtest.me/ and scales on its request rate through KEDA.
