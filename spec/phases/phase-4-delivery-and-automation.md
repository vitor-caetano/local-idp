# Phase 4: Delivery and automation

**Goal:** The engines the golden path runs on: Argo Workflows for CI, Argo Events for triggers, Argo
Rollouts for canaries, KEDA for scaling.

**Outputs:**
- `argo-workflows` (server auth mode, workflows in `ci` with the `ci-runner` service account)
- `argo-events` (controller and CRDs only; the EventBus arrives with the golden path)
- `argo-rollouts`, `keda`
- `gitea-config`: the `services` org, the automation token in `argocd`, `ci` and `backstage`, and
  the org webhook pointing at the Argo Events EventSource

**Test criteria (`tests/test_phase_4_delivery_and_automation.py`):**
- The five Applications are Synced and Healthy
- A hello-world Workflow submitted to `ci` as `ci-runner` Succeeds
- The Rollout and ScaledObject CRDs are Established
- `Secret/gitea-scm-token` in `argocd` and `Secret/gitea-ci-credentials` in `ci` exist
- The `services` org in Gitea has a push webhook to `gitea-eventsource-svc.argo-events.svc:12000`

**Completion promise:** `<promise>PHASE4_DONE</promise>`

**Key decisions:**
- Rollouts canary by replica weight, with no traffic-router plugin. Simpler, and enough to see a
  canary step.
- KEDA triggers on Prometheus. Kind has no metrics-server, so CPU triggers read nothing.
- Gitea's `webhook.ALLOWED_HOST_LIST: private` is required, or webhook delivery to a ClusterIP is
  silently refused.

**Stop here.**
