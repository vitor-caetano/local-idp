package main

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func get(t *testing.T, h http.Handler, path string) *httptest.ResponseRecorder {
	t.Helper()
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, path, nil))
	return rec
}

func TestRootGreets(t *testing.T) {
	rec := get(t, (&server{}).routes(), "/")
	if rec.Code != http.StatusOK {
		t.Fatalf("GET / = %d, want 200", rec.Code)
	}
	if !strings.Contains(rec.Body.String(), serviceName) {
		t.Fatalf("GET / body %q does not name the service", rec.Body.String())
	}
}

func TestHealthz(t *testing.T) {
	if rec := get(t, (&server{}).routes(), "/healthz"); rec.Code != http.StatusOK {
		t.Fatalf("GET /healthz = %d, want 200", rec.Code)
	}
}

func TestMetricsCountsRootRequests(t *testing.T) {
	h := (&server{}).routes()
	get(t, h, "/")
	get(t, h, "/")
	body := get(t, h, "/metrics").Body.String()
	if !strings.Contains(body, "http_requests_total 2\n") {
		t.Fatalf("metrics did not count two requests:\n%s", body)
	}
}

func TestUnknownPathIs404(t *testing.T) {
	if rec := get(t, (&server{}).routes(), "/nope"); rec.Code != http.StatusNotFound {
		t.Fatalf("GET /nope = %d, want 404", rec.Code)
	}
}
