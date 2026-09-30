# Prompt Library

The prompts that drive each phase, in order. Each says what a good response looks like and what
usually goes wrong.

## Two rules the prompts assume

**GitOps.** Your agent writes manifests to `platform/`, commits, and pushes with
`./provision/push-to-cluster.sh`. It does not run mutating `kubectl`. `.claude/settings.json` makes
it ask before any `kubectl apply`, `helm install`, `git push` or `./provision/*` script; that pause
is the policy working.

**Context.** Every command uses `KUBECONFIG=$HOME/.kube/local-idp`. If the agent reaches for
`~/.kube/config` or another context, stop it.

---

## Phase 0: preflight and cluster

> Read `spec/BUILD-SPEC.md`, `spec/phases/phase-0-preflight.md` and `components.yaml`. Run
> `tests/test_phase_0_preflight.py` and show me it fails. Then run `./provision/create-cluster.sh`,
> run the test again, and stop.

**Good:** reads first, runs the test against no cluster (skips or fails), runs the script once, and
reports the three nodes and the registry check.
**Goes wrong:** the VM check fails. Resize Rancher Desktop, do not lower the threshold.

## Phase 1: GitOps and traffic

> Create `platform/` from `solution/platform/` and walk me through the foundation App-of-Apps and
> its sync waves in a few sentences. Then set the Git source to gitea, bootstrap ArgoCD, build the
> Backstage image, seed Gitea, and run the phase 1 test. Stop when it passes.

**Good:** explains that `platform-foundation` recurses `platform/1-foundation` for
`*/application.yaml`, and that the Application health check makes each wave wait. Builds the image
before seeding.
**Goes wrong:** seeding before the image exists. Backstage then sits in ImagePullBackOff and holds
wave 6. Build and push the image; ArgoCD recovers on its own.

## Phase 2: secrets and policy

> Show me how the Backstage Postgres password gets from OpenBao into the Postgres pod without
> appearing in Git. Then run the phase 2 test.

**Good:** traces the seed Job, `secret/backstage-postgres`, the ExternalSecret, the Secret, and the
StatefulSet's `envFrom`.

## Phase 3: observability

> Run the phase 3 test. Then open Grafana at https://grafana.localtest.me and find the span the test
> sent.

**Goes wrong:** Loki has no lines. Check the Alloy pod's logs before Loki.

## Phase 4: delivery and automation

> Run the phase 4 test and explain what gitea-config did to Gitea, ArgoCD and the ci namespace.

## Phase 5: portal

> Trust the local CA with `./provision/trust-ca.sh --install`, then run the phase 5 test. Open Backstage and
> find the Go service template.

## Phase 6: golden path

> Apply `platform/0-bootstrap/self-service-app.yaml`. When the self-service Applications are
> Healthy, I will scaffold `hello-go` in Backstage. Then follow it: the webhook delivery in Gitea,
> the Sensor, the Workflow, the image in the registry, the tag commit, the Rollout. Run the phase 6
> test.

**Goes wrong:** no Workflow appears. Check the webhook's recent deliveries in Gitea first
(`webhook.ALLOWED_HOST_LIST`), then the Sensor pod's logs.

## Phase 7: governance

> Flip every `failureAction` in the golden-path policies to Enforce, commit, and push. When
> `golden-path-policies` is Synced, run `./scripts/denial-demo.sh`, then the phase 7 test.

**Good:** changes only the `golden-path-*` set. The baseline stays Audit.
