package main

import (
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func get(t *testing.T, srv *httptest.Server, path string) (int, string) {
	t.Helper()
	res, err := http.Get(srv.URL + path)
	if err != nil {
		t.Fatal(err)
	}
	defer res.Body.Close()
	body, err := io.ReadAll(res.Body)
	if err != nil {
		t.Fatal(err)
	}
	return res.StatusCode, string(body)
}

func TestRootGreets(t *testing.T) {
	srv := httptest.NewServer(newMux(newRequestCounter()))
	defer srv.Close()
	code, body := get(t, srv, "/")
	if code != http.StatusOK || body != "hello from "+serviceName+"\n" {
		t.Fatalf("got %d %q", code, body)
	}
}

func TestUnknownPathIsNotFound(t *testing.T) {
	srv := httptest.NewServer(newMux(newRequestCounter()))
	defer srv.Close()
	if code, _ := get(t, srv, "/nope"); code != http.StatusNotFound {
		t.Fatalf("got %d, want 404", code)
	}
}

func TestMetricsCountRequests(t *testing.T) {
	srv := httptest.NewServer(newMux(newRequestCounter()))
	defer srv.Close()
	get(t, srv, "/")
	get(t, srv, "/")
	_, body := get(t, srv, "/metrics")
	if !strings.Contains(body, `http_requests_total{path="/",code="200"} 2`) {
		t.Fatalf("metrics did not count two requests:\n%s", body)
	}
}

func TestMetricsExistBeforeAnyRequest(t *testing.T) {
	srv := httptest.NewServer(newMux(newRequestCounter()))
	defer srv.Close()
	_, body := get(t, srv, "/metrics")
	if !strings.Contains(body, `http_requests_total{path="/",code="200"} 0`) {
		t.Fatalf("the / series is missing before the first request:\n%s", body)
	}
}
