# Phase 5: Developer portal

**Goal:** Backstage running from the local registry, its catalog in Postgres, every platform UI
reachable at `https://<name>.localtest.me`. That completes the foundation.

**Outputs:**
- `localhost:5001/local-idp/backstage:0.1.2`, built in phase 1 by `images/backstage/build-and-push.sh`
  (this phase is where you open it and check it, and where you rebuild it if you add plugins)
- `backstage-config`: Postgres with credentials from OpenBao, the Backstage service account and its
  read-only ClusterRole, and the `argocd-token` Job. The Job signs in as admin with
  `argocd-initial-admin-secret`, mints a token for the read-only `backstage` ArgoCD account, and
  stores it as `backstage/argocd-credentials`. A rerun keeps a stored token that ArgoCD still accepts
- `backstage` Synced and Healthy. It reads the token as `ARGOCD_AUTH_TOKEN`, which the image's
  `/argocd/api` proxy sends. Its chart `appConfig` limits the ArgoCD tab and the two ArgoCD cards to
  entities annotated `argocd/app-name`: `app.packages: all` discovers them with no filter, and they
  would otherwise show on every Component
- `platform-routes`: HTTPRoutes for argocd, gitea, grafana, workflows, backstage
- The local CA exported and trusted with `./provision/trust-ca.sh --install` (optional, for
  the browser)

**Test criteria (`tests/test_phase_5_portal.py`):**
- `backstage-config`, `backstage`, `platform-routes` Synced and Healthy
- Every HTTPRoute in the cluster is Accepted with ResolvedRefs
- From the host, each of the five hostnames answers over HTTPS with the local CA
- The Backstage catalog API lists the `platform-team` Group and the `go-service` Template
- The token in `backstage/argocd-credentials` signs in to ArgoCD as `backstage`, and Backstage's
  `/api/proxy/argocd/api` returns the `backstage` Application

Cluster-free, `tests/test_portal_wiring.py` checks the token wiring, the read-only role and the
`appConfig` filter, in both `solution/platform/` and your `platform/`.

**Completion promise:** `<promise>PHASE5_DONE</promise>`

**Key decisions:**
- The Backstage chart's Bitnami PostgreSQL is off. A plain StatefulSet reads its password from
  OpenBao through an ExternalSecret, and Backstage reads the same Secret.
- Guest sign-in, for a single-person cluster.
- The catalog reads the template from `PLATFORM_RAW_BASE`, which the Git source switch sets.
- The ArgoCD tab uses an account token, which carries no expiry, so it keeps working after the
  first day. The admin password is read only to mint it.

**Stop here.** You have a working IDP. The next phase makes it self-service.
