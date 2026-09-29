# Phase 7: Governance

**Goal:** Turn the golden-path policies from reporting to blocking, and show that a workload which
bypasses the golden path is denied while a scaffolded service still deploys.

**Outputs:**
- In `platform/2-self-service/golden-path-policies/manifests/golden-path-policies.yaml`, every
  `failureAction: Audit` changed to `Enforce`, committed and pushed
- `scripts/denial-demo.sh` run: it applies a Pod with `docker.io/library/nginx:latest` into `apps`
  and shows the admission error (the one sanctioned mutating `kubectl` in the build)
- A new commit to `hello-go` rolled out under enforcement

**Test criteria (`tests/test_phase_7_governance.py`):**
- Every rule in the three `golden-path-*` ClusterPolicies is `Enforce`
- Every rule in the `policy-baseline` ClusterPolicies is still `Audit`
- A server-side dry-run of a Pod with `docker.io/library/nginx:latest` in `apps` is denied, and the
  message names `golden-path-restrict-registries`
- A server-side dry-run of the same Pod in `default` is admitted (scope is the label, not the cluster)
- `svc-hello-go` is still Synced and Healthy

**Completion promise:** `<promise>PHASE7_DONE</promise>`

**Key decisions:**
- The baseline stays Audit. Enforcing hygiene rules on a laptop cluster teaches nothing the golden
  path does not already do.
- The flip is a Git commit, so it has an author, a review point and a revert.

**Stop here.** The platform is complete.
