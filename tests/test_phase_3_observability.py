# ABOUTME: Phase 3 gate. Prometheus scraping, Alloy shipping logs to Loki, a span sent through the
# ABOUTME: collector landing in Tempo, and Grafana wired to all three.
import json
import secrets
import time

from conftest import assert_apps_healthy, incluster_curl, wait_for


def test_observability_apps_healthy():
    assert_apps_healthy("kube-prometheus-stack", "loki", "alloy", "tempo",
                        "opentelemetry-collector")


def test_prometheus_scrapes_kube_state_metrics():
    body, code = incluster_curl(
        "http://kube-prometheus-stack-prometheus.observability.svc:9090/api/v1/query",
        "--get", "--data-urlencode", 'query=up{job="kube-state-metrics"} == 1',
        ns="observability",
    )
    assert code == "200", body
    assert json.loads(body)["data"]["result"], "kube-state-metrics is not up in Prometheus"


def test_loki_has_argocd_logs():
    def found():
        body, code = incluster_curl(
            "http://loki-gateway.observability.svc/loki/api/v1/query_range",
            "--get", "--data-urlencode", 'query={namespace="argocd"}',
            "--data-urlencode", "limit=1", ns="observability",
        )
        return code == "200" and json.loads(body)["data"]["result"]
    wait_for(found, timeout=300, interval=15, message="argocd log lines in Loki")


def test_span_reaches_tempo():
    # Tempo has no persistence, so the test produces the span it looks for.
    trace_id = secrets.token_hex(16)
    now = time.time_ns()
    payload = {"resourceSpans": [{
        "resource": {"attributes": [{"key": "service.name",
                                     "value": {"stringValue": "phase3-probe"}}]},
        "scopeSpans": [{"spans": [{
            "traceId": trace_id, "spanId": secrets.token_hex(8), "name": "phase3-probe",
            "kind": 1, "startTimeUnixNano": str(now - 1_000_000), "endTimeUnixNano": str(now),
        }]}],
    }]}
    _, code = incluster_curl(
        "http://opentelemetry-collector.observability.svc:4318/v1/traces",
        "-X", "POST", "-H", "Content-Type: application/json", "--data", json.dumps(payload),
        ns="observability",
    )
    assert code == "200", f"collector refused the span: {code}"

    def found():
        _, code = incluster_curl(f"http://tempo.observability.svc:3200/api/traces/{trace_id}",
                                 ns="observability")
        return code == "200"
    wait_for(found, timeout=120, interval=10, message=f"trace {trace_id} in Tempo")


def test_grafana_has_three_datasources():
    body, code = incluster_curl(
        "http://kube-prometheus-stack-grafana.observability.svc/api/datasources",
        "-u", "admin:local-dev-only", ns="observability",
    )
    assert code == "200", body
    types = {d["type"] for d in json.loads(body)}
    assert {"prometheus", "loki", "tempo"} <= types, types
