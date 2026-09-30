# Phase 5: Developer portal

**Goal:** Backstage running from the local registry, its catalog in Postgres, every platform UI
reachable at `https://<name>.localtest.me`. That completes the foundation.

**Outputs:**
- `localhost:5001/local-idp/backstage:0.1.2`, built in phase 1 by `images/backstage/build-and-push.sh`
  (this phase is where you open it and check it, and where you rebuild it if you add plugins)
- `backstage-config`: Postgres with credentials from OpenBao, the Backstage service account and its
  read-only ClusterRole
- `backstage` Synced and Healthy
- `platform-routes`: HTTPRoutes for argocd, gitea, grafana, workflows, backstage
- The local CA exported and trusted with `./provision/trust-ca.sh --install` (optional, for
  the browser)

**Test criteria (`tests/test_phase_5_portal.py`):**
- `backstage-config`, `backstage`, `platform-routes` Synced and Healthy
- Every HTTPRoute in the cluster is Accepted with ResolvedRefs
- From the host, each of the five hostnames answers over HTTPS with the local CA
- The Backstage catalog API lists the `platform-team` Group and the `go-service` Template

**Completion promise:** `<promise>PHASE5_DONE</promise>`

**Key decisions:**
- The Backstage chart's Bitnami PostgreSQL is off. A plain StatefulSet reads its password from
  OpenBao through an ExternalSecret, and Backstage reads the same Secret.
- Guest sign-in, for a single-person cluster.
- The catalog reads the template from `PLATFORM_RAW_BASE`, which the Git source switch sets.

**Stop here.** You have a working IDP. The next phase makes it self-service.
