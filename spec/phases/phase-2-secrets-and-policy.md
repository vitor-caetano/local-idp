# Phase 2: Secrets and policy

**Goal:** OpenBao as the secret backend, External Secrets pulling from it, and Kyverno installed with
nothing enforcing.

**Inputs:** Phase 1 complete. The whole foundation started syncing when Gitea was seeded, so these
components are already converging. Phases 2 to 5 each prove one slice of it, in the order a reader
can understand it, not the order ArgoCD installs it.

**Outputs:**
- `openbao` (dev mode), `external-secrets`, `kyverno` Synced and Healthy
- `openbao-config`: the `openbao` ClusterSecretStore, a seed Job that writes `secret/demo` and
  generates `secret/backstage-postgres`, and the demo ExternalSecret
- `policy-baseline`: four Audit ClusterPolicies scoped to namespaces labelled
  `local-idp.dev/policy=enforce` (only `apps`)

**Test criteria (`tests/test_phase_2_secrets_and_policy.py`):**
- The four Applications above are Synced and Healthy (`policy-baseline` arrives in wave 6, so this
  may wait on phases 3 to 5 converging first; the test allows for it)
- `ClusterSecretStore/openbao` Ready
- `Secret/demo-app-credentials` exists in `openbao` and holds the seeded username
- Every ClusterPolicy in the cluster has every rule at `failureAction: Audit`
- A privileged pod in `apps` is admitted (Audit does not block) and produces a policy report entry

**Completion promise:** `<promise>PHASE2_DONE</promise>`

**Key decisions:**
- OpenBao, not Vault: Vault relicensed to BUSL; OpenBao is the LF/MPL-2.0 fork.
- Dev mode is in-memory. A restart empties it; ExternalSecrets keep what they already wrote.
- Install first, enforce last. The baseline stays Audit permanently.

**Stop here.**
