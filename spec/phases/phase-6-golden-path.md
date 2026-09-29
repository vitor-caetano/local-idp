# Phase 6: Golden path

**Goal:** Scaffold a Go service in Backstage and watch it test, build, deploy as a canary, and scale,
with no step outside Git.

**Outputs:**
- `platform/0-bootstrap/self-service-app.yaml` applied (the second sanctioned direct apply of a
  plane root)
- `ci-pipeline`: JetStream EventBus, the `gitea` webhook EventSource, the `ci-go-service` Sensor and
  WorkflowTemplate
- `golden-path-deploy`: the `golden-path-services` AppProject and ApplicationSet
- `golden-path-policies` in Audit
- A service named `hello-go` scaffolded from the Backstage template

**Test criteria (`tests/test_phase_6_golden_path.py`):**
- The three self-service Applications are Synced and Healthy
- EventBus, EventSource and Sensor report every condition True
- Given `hello-go` exists in the `services` org (the test tells you to scaffold it if not):
  - a `ci-go-service` Workflow for it Succeeded
  - `localhost:5001/services/hello-go` has at least one tag
  - `svc-hello-go` is Synced and Healthy, and its Rollout is Healthy
  - `https://hello-go.localtest.me/` answers `hello from hello-go`
  - Prometheus has a `http_requests_total` series for it

**Completion promise:** `<promise>PHASE6_DONE</promise>`

**Key decisions:**
- The CI pipeline commits the image tag back to the service repo with `[skip ci]`, and the Sensor
  filters that out. GitOps stays the only path to a deploy.
- BuildKit rootless needs seccomp and AppArmor unconfined, so `ci` is a privileged Pod Security
  namespace and nothing else runs there.
- The generated service uses only the Go standard library, so there is no `go.sum` to manage.

**Verify when building:** the Sensor's `comparator: "!="` on a string data filter, and the Gitea
push payload keys (`body.head_commit.message`, `body.repository.clone_url`, `body.after`), against
the pinned Argo Events and Gitea versions.

**Stop here.**
