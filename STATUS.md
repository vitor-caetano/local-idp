# Status

Where the build stands. Update this file when a phase completes.

## As of 2026-10-14

**Rebuild complete. Phase 7 done; the platform is complete again,** on a `platform/` regenerated
from `spec/` (path B) rather than copied from `solution/`. All 30 Applications are Synced and
Healthy. Phases 1 and 3 to 7 pass. Phase 0's `test_cluster_is_bare` and two phase 2 checks now fail
by design, because they assert the state before ArgoCD and before enforcement. The section for
each phase follows. The 2026-09-30 build further down is history: its fixes still hold, and its
claims about a running cluster describe the cluster that was destroyed.

**Phase 0 passed again** (5 of 5). Kind `local-idp` on `kindest/node:v1.36.4`: three nodes Ready,
`kind-registry` on `localhost:5001` reachable from pods as `kind-registry:5000`, inotify raised from
128 to 512. The cluster is bare: namespaces `default`, `kube-system`, `kube-public`,
`kube-node-lease` and `local-path-storage`, 13 system pods. The first run failed once because a
worker had joined seconds earlier and was not Ready yet; the rerun passed.

**Phase 1 passed again** (6 of 6), on a `platform/` generated from the spec. The phase needs the
whole foundation tree, not only the traffic components: `set-git-source.sh` reads the Backstage
Application, and seeding starts every wave. All 25 Applications (waves 0 to 6) are Synced and
Healthy. What differs from the earlier build:

- Gitea's `ROOT_URL` is `http://gitea-http.gitea.svc:3000/`, so the clone URLs Gitea hands to
  ArgoCD, CI and the SCM generator resolve inside pods. The UI is still at `gitea.localtest.me`.
- The OpenBao root token is written once, in the chart values, and templated into the
  `openbao-root-token` Secret through the chart's `extraObjects`.
- Argo Workflows installs its minified CRDs as ordinary resources (`crds.full: false`) instead of
  the full ones, which the chart applies from a hook Job that downloads them from GitHub.
- `gitea-config` runs in `alpine/k8s:1.36.4`, now pinned in `components.yaml` as `job-tools`.
- Four Applications read OutOfSync while Healthy. ESO and Kyverno webhooks add defaults, so the
  ExternalSecrets and ClusterPolicies now spell them out. `argocd-values.yaml` ignores only what
  cannot live in Git: the CRD `conversion: None` default, the empty metadata maps the Kyverno
  chart renders on its CRDs, and Kyverno's deprecated spec-level `validationFailureAction`.
- `ARGOCD_AUTH_TOKEN` is not set for Backstage. The ArgoCD tab it serves is not wired (see Known
  open items), so nothing reads it yet.

**Phase 2 passed again** (6 of 6) on its first run, with no changes: its components converged
during phase 1, so there was no failing run to see first. The `openbao-seed` Job generated
`secret/backstage-postgres`. Its hash matches in OpenBao, the `backstage-postgres` Secret, and the
Postgres container, and a password login to Postgres succeeds. The four baseline ClusterPolicies are
Ready, every rule in Audit.

**Phase 3 passed again** (5 of 5) on its first run, with no changes, for the same reason. All 20
active Prometheus targets are up, none down: etcd, the scheduler, the controller manager and
kube-proxy are disabled rather than left failing. Loki holds logs from every namespace that runs a
pod, so Alloy's single replica is reading the whole cluster.

**Phase 4 passed again** (5 of 5) on its first run, with no changes. `gitea-config` created the
`services` org and wrote one automation token to `argocd/gitea-scm-token`,
`ci/gitea-ci-credentials` and `backstage/gitea-credentials`. The token authenticates against the
Gitea API (200 on `/api/v1/user`). The org has one active push webhook, to
`gitea-eventsource-svc.argo-events.svc:12000/push`. Nothing listens there until phase 6 adds the
EventSource.

**Phase 5 passed again** (4 of 4). The first run failed only the catalog check: Backstage reads the
`platform-team` Group and the `go-service` Template from `platform/2-self-service/`, which the
generated tree did not have yet. Phase 5 brings that part of phase 6 forward: `catalog/org.yaml`,
`go-service/template.yaml`, and the full skeleton, so a template run in the UI produces a working
repo. Rendered as Backstage would, the skeleton passes `go vet`, `go test` and `kustomize build`.
7 of the 9 template contract tests pass against `platform/`; the other two read the AppProject and
the WorkflowTemplate, which arrive in phase 6. Backstage, Postgres and the five routes needed no
changes.

**Phase 6 passed again** (9 of 9). Before the build, 4 checks failed and 5 skipped. The
self-service plane is generated: `self-service-app.yaml` (applied once), `ci-pipeline`,
`golden-path-deploy` and `golden-path-policies` (Audit), all Synced and Healthy. `hello-go` was
scaffolded through the Backstage scaffolder API, signed in as guest, which is the call the UI's
Create button makes. All three template steps completed. The scaffold push triggered
`ci-go-service`, which succeeded. CI's `[skip ci]` tag commit arrived 85 seconds later, and the
Sensor dropped it as filtered: two pushes, one Workflow. `svc-hello-go` is Synced and Healthy, KEDA
holds the Rollout at 2 replicas, and its pods pass all seven policies.

- Verified against the pinned source, as the spec asks: in Argo Events v1.9.10 a string data
  filter value is an unanchored regular expression, and `comparator: "!="` passes on no match. The
  ref filter is anchored (`^refs/heads/main$`) for that reason. The Gitea push payload keys
  `body.repository.name`, `body.repository.clone_url` and `body.after` filled the Workflow's
  parameters.
- One defect, found by the last check: the service's `http_requests_total` series did not exist
  until its first request, so Prometheus and the KEDA query saw nothing for an idle service, and the
  test read Prometheus before its own request had been scraped. The skeleton now starts the `/`
  series at zero, with a test for it. `hello-go` still runs the old code; phase 7's "new commit
  under enforcement" carries the fix to it.

**Phase 7 passed again** (5 of 5). Before the flip, 2 failed. One commit moved the three
`golden-path-*` ClusterPolicies to `Enforce`; `policy-baseline` stays `Audit`.
`scripts/denial-demo.sh` shows the `docker.io/library/nginx:latest` Pod denied in `apps` by all
three policies and admitted in `default`. The new `hello-go` commit (`d262843`, the skeleton's
zero-counter fix) was built by `ci-go-service` and rolled out as a canary under enforcement, to
`hello-go:d26284332dbc`. CI's tag commit was filtered again: one build per real push. Phases 1, 3,
4, 5 and 6 still pass under enforcement. Two phase 2 checks fail by design: one asserts every rule
is Audit, and the other expects a bare pod to be admitted into `apps`.

| Phase | Rebuild |
|---|---|
| 0 Preflight and cluster | Done 2026-10-14 |
| 1 GitOps and traffic | Done 2026-10-14 |
| 2 Secrets and policy | Done 2026-10-14 |
| 3 Observability | Done 2026-10-14 |
| 4 Delivery and automation | Done 2026-10-14 |
| 5 Developer portal | Done 2026-10-14 |
| 6 Golden path | Done 2026-10-14 |
| 7 Governance | Done 2026-10-14 |

## As of 2026-09-30

**Phase 7 done. The platform is complete.** `tests/test_phase_7_governance.py` passes (5 of 5), and
phase 6 still passes (9 of 9) under enforcement. The three `golden-path-*` ClusterPolicies are
`Enforce` in `platform/` (commit `ba48201`); `policy-baseline` stays `Audit`, and `solution/` keeps
shipping `Audit` as `tests/test_policies.py` requires. `scripts/denial-demo.sh` shows a
`docker.io/library/nginx:latest` Pod denied in `apps` by all three policies and admitted in
`default`. A new `hello-go` commit (`cab55269`) built and rolled out as a canary under enforcement.

**Phase 6.** `tests/test_phase_6_golden_path.py` passes (9 of 9), and phases 1 to 5 still pass
(26 of 26). `hello-go` was scaffolded in Backstage, built by `ci-go-service` in about 50 seconds,
and deployed as `svc-hello-go`; `https://hello-go.localtest.me/` answers `hello from hello-go`. All 30
Applications are Synced and Healthy. The loop guard holds: two push events, one Workflow, because
the Sensor's `comparator: "!="` drops the pipeline's `[skip ci]` commit.

**Phase 5.** `tests/test_phase_5_portal.py` passes (4 of 4). The foundation is complete: every
UI answers over HTTPS with the local CA. The catalog check called the Backstage API with no
credentials, which the new backend refuses (401). It now signs in as guest first, the way the
browser does. The platform needed no change.

**Phase 4.** `tests/test_phase_4_delivery_and_automation.py` passes (5 of 5) with no
changes: Argo Workflows, Events, Rollouts, KEDA and the `gitea-config` seed had converged already.

**Phase 3.** `tests/test_phase_3_observability.py` passes (5 of 5). The observability stack
needed no changes. The test harness did: `incluster_curl` ran `kubectl run --rm -i`, and kubectl
1.36 streams a fast pod's output twice (attach plus the logs fallback), so JSON bodies failed to
parse. It now runs the pod detached and reads its logs once.

**Phase 2.** `tests/test_phase_2_secrets_and_policy.py` passes (6 of 6) with no changes: its
components had converged during phase 1. The Backstage Postgres password is generated by the
`openbao-seed` Job, and its hash matches in OpenBao, the `backstage-postgres` Secret, and the Postgres
container.

**Phase 1.** ArgoCD reads `platform/` from the in-cluster Gitea, and all 25 foundation
Applications (waves 0 to 6) are Synced and Healthy. `tests/test_phase_1_gitops_and_traffic.py`
passes (6 of 6): `http://gitea.localtest.me` answers 301 to https from the host. The Backstage image
`localhost:5001/local-idp/backstage` is built from Backstage 1.51.2 (tag 0.1.0 then; 0.1.2 after the
phase 6 fixes). The repo is public at
https://github.com/vitor-caetano/local-idp.

Phase 0's `test_cluster_is_bare` now fails by design: it asserts the pre-ArgoCD state.

Tools come from `devbox.json` (see `docs/prerequisites.md`).

| Phase | State |
|---|---|
| 0 Preflight and cluster | Done 2026-09-29 |
| 1 GitOps and traffic | Done 2026-09-30 |
| 2 Secrets and policy | Done 2026-09-30 |
| 3 Observability | Done 2026-09-30 |
| 4 Delivery and automation | Done 2026-09-30 |
| 5 Developer portal | Done 2026-09-30 |
| 6 Golden path | Done 2026-09-30 |
| 7 Governance | Done 2026-09-30 |

## Added after the build

- **`docs/golden-path.html`**: a visual walkthrough of the golden path, one diagram per stage, from
  the Backstage template through the Gitea repo, Argo Events, the CI Workflow, the ApplicationSet,
  the canary Rollout, and the request and scaling paths, plus the enforced policies and where to look
  when a stage breaks. Open it locally with `open docs/golden-path.html`. A private published copy
  is at https://claude.ai/artifact/K8hbUCeF8JLtRnbn6sZcLz; republish it after editing the file.
- **Trusting the local CA is scripted.** `./provision/trust-ca.sh --install` trusts the root in the
  macOS login keychain (no sudo; one password dialog), after removing any older
  `local-idp-root-ca`, since every cluster generates a new CA under that name. `--remove` takes it
  out, and `./provision/destroy.sh` now does too, along with `provision/local-idp-ca.crt`. A copy in
  the System keychain is reported, not removed, because that needs sudo. The helpers are
  `trust_ca` and `untrust_ca` in `provision/lib.sh`.

## Next steps

1. Nothing is required. To rebuild from scratch, `./provision/destroy.sh` and start at phase 0; the
   fixes recorded below are all in Git. After phase 1, run `./provision/trust-ca.sh --install` so the
   browser trusts `*.localtest.me`.
2. The inotify limits reset when the Rancher Desktop VM restarts. `create-cluster.sh` raises them on
   a new cluster; after a restart with the cluster still there, run `devbox run resume`
   (`provision/resume-cluster.sh`), which raises them and recovers the pods and OpenBao.

## Unproven until the first build

These were resolved from upstream on 2026-09-29 and have never run on this platform. If one fails,
fix the pin in `components.yaml` and the Application, then run `scripts/gen-versions-lock.py`.

| Item | Where it bites |
|---|---|
| Nothing left. BuildKit rootless, the Sensor filter and the Gitea payload keys were proven in phase 6. | |

Components shared with the EKS sibling platform (ArgoCD, Gitea, cert-manager, OpenBao, ESO,
Kyverno, the observability charts, the Argo charts, KEDA, Backstage) reuse pins that build validated.

## Fixed during phase 1

Each was a defect in the reference build too. The manifest fixes are mirrored in `solution/`; the
Backstage fixes are in the shared `images/backstage/build-and-push.sh`.

- **Backstage build floated to the newest release.** `create-app@latest` scaffolded 1.55.0, and the
  scaffold's caret ranges mixed releases even when pinned (TS2742). `build-and-push.sh` now pins
  create-app 0.8.3 and every `@backstage` package to the 1.51.2 manifest through `resolutions`.
- **`@yarnpkg/core` 4.9.2 is broken upstream** (a `patch:` dependency on a file only in Yarn's repo).
  Pinned to 4.9.1 in the same `resolutions`. Drop the pin once a fixed release ships.
- **`yarn --cwd` ran yarn 1.** Corepack picks the version from the starting directory. The script
  now runs yarn inside the app.
- **Permanent OutOfSync on the Gateway, every HTTPRoute, and the Postgres StatefulSet.** The API
  server defaults fields Git omitted. The manifests now spell them out. Server-side diff was tried
  and did not absorb them.
- **The host timed out on port 80.** Envoy Gateway defaults the Service to
  `externalTrafficPolicy: Local`, and Kind maps host ports onto the control plane while Envoy runs on
  a worker. The EnvoyProxy now sets `Cluster`.

## Fixed during phase 6

Each is mirrored in `solution/`. Phase 5's API test could not catch the Backstage ones, because it
never loads the UI or runs a template.

- **Backstage UI crashed** with `No implementation available for apiRef{plugin.notifications.service}`.
  The pod loads `app-config.production.yaml` alone, which lacked `app.packages: all`, so the new
  frontend system installed only the catalog. Added it, and registered the notifications, signals
  and search backends the discovered plugins call. Image 0.1.1.
- **Every template task failed at step one.** The scaffolder needs `NODE_OPTIONS=--no-node-snapshot`
  on Node 20+; the platform Dockerfile had dropped it. Image 0.1.2.
- **`publish:gitea` requires `description`.** The form field is optional; it now has a default and a
  fallback.
- **`catalog:register` got a 400.** `publish:gitea`'s `repoContentsUrl` drops the branch. The
  template now passes an explicit `catalogInfoUrl`.
- **The Sensor could not submit.** `ci-sensor` lacked `get` on `workflowtemplates`.
- **`svc-<name>` was InvalidSpecError.** The SCM generator's `.url` is the SSH URL
  (`git@git.example.com:...`) by default. The ApplicationSet now sets `cloneProtocol: https`.
- **`svc-hello-go` read OutOfSync.** The skeleton omitted API defaults: the HTTPRoute's (fixed before
  the scaffold) and the Rollout's `ports[].protocol` (fixed in the skeleton and, with a `[skip ci]`
  commit, in the `hello-go` repo).

## Known open items

- The Backstage ArgoCD and Kubernetes tabs are installed but not wired into the entity page. See
  `images/backstage/README.md`.
