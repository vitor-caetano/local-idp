# Phase 3: Observability

**Goal:** Metrics, logs and traces flowing into Grafana.

**Outputs:**
- `kube-prometheus-stack` with Loki and Tempo datasources, selecting every ServiceMonitor
- `loki` (SingleBinary), `alloy` shipping every pod's logs to it
- `tempo` with OTLP receivers, `opentelemetry-collector` forwarding OTLP to Tempo

**Test criteria (`tests/test_phase_3_observability.py`):**
- The five Applications are Synced and Healthy
- Prometheus has at least one `up == 1` target for kube-state-metrics
- Loki returns log lines for the `argocd` namespace (Alloy is shipping)
- A span sent by the test to the collector over OTLP HTTP is found in Tempo. The test produces the
  span it looks for, because Tempo has no persistence and a restart empties it.
- Grafana lists Prometheus, Loki and Tempo datasources

**Completion promise:** `<promise>PHASE3_DONE</promise>`

**Key decisions:**
- Kind binds etcd, the scheduler, the controller manager and kube-proxy metrics to loopback, so
  those scrape targets are disabled rather than left permanently down.
- Alloy, not Promtail (deprecated). One Deployment replica reading through the Kubernetes API, so no
  hostPath mounts and no duplicate lines.
- Tempo is held at chart 1.25.0 (see `components.yaml`).

**Stop here.**
