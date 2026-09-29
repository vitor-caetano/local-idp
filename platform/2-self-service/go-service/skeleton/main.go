// Command ${{ values.name }} is a golden-path HTTP service.
//
// Standard library only, so there is no go.sum to keep in step and the CI build needs no module
// download. /metrics writes the Prometheus text format by hand for the one counter KEDA scales on.
package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
	"sync/atomic"
	"time"
)

const serviceName = "${{ values.name }}"

type server struct {
	requests atomic.Uint64
}

func (s *server) routes() *http.ServeMux {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /{$}", s.handleRoot)
	mux.HandleFunc("GET /healthz", handleHealthz)
	mux.HandleFunc("GET /metrics", s.handleMetrics)
	return mux
}

func (s *server) handleRoot(w http.ResponseWriter, _ *http.Request) {
	s.requests.Add(1)
	fmt.Fprintf(w, "hello from %s\n", serviceName)
}

func handleHealthz(w http.ResponseWriter, _ *http.Request) {
	fmt.Fprintln(w, "ok")
}

func (s *server) handleMetrics(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "text/plain; version=0.0.4")
	fmt.Fprintln(w, "# HELP http_requests_total Requests served on /.")
	fmt.Fprintln(w, "# TYPE http_requests_total counter")
	fmt.Fprintf(w, "http_requests_total %d\n", s.requests.Load())
}

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	srv := &http.Server{
		Addr:              ":" + port,
		Handler:           (&server{}).routes(),
		ReadHeaderTimeout: 5 * time.Second,
	}
	log.Printf("%s listening on %s", serviceName, srv.Addr)
	log.Fatal(srv.ListenAndServe())
}
