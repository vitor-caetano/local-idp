// ${{ values.name }}: ${{ values.description }}
//
// A golden-path service from local-idp. Standard library only, so there is no go.sum to keep
// current. It answers on / and serves its own request counter on /metrics in the Prometheus text
// format; the ServiceMonitor adds the service label when Prometheus scrapes it.
package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
	"sort"
	"sync"
)

const serviceName = "${{ values.name }}"

// requestCounter counts handled requests by path and status code.
type requestCounter struct {
	mu     sync.Mutex
	counts map[[2]string]uint64
}

func newRequestCounter() *requestCounter {
	return &requestCounter{counts: make(map[[2]string]uint64)}
}

func (c *requestCounter) inc(path string, code int) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.counts[[2]string{path, fmt.Sprint(code)}]++
}

func (c *requestCounter) ServeHTTP(w http.ResponseWriter, _ *http.Request) {
	c.mu.Lock()
	keys := make([][2]string, 0, len(c.counts))
	for k := range c.counts {
		keys = append(keys, k)
	}
	sort.Slice(keys, func(i, j int) bool { return keys[i][0]+keys[i][1] < keys[j][0]+keys[j][1] })
	w.Header().Set("Content-Type", "text/plain; version=0.0.4")
	fmt.Fprintln(w, "# HELP http_requests_total Requests handled, by path and status code.")
	fmt.Fprintln(w, "# TYPE http_requests_total counter")
	for _, k := range keys {
		fmt.Fprintf(w, "http_requests_total{path=%q,code=%q} %d\n", k[0], k[1], c.counts[k])
	}
	c.mu.Unlock()
}

func newMux(counter *requestCounter) *http.ServeMux {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /{$}", func(w http.ResponseWriter, _ *http.Request) {
		fmt.Fprintf(w, "hello from %s\n", serviceName)
		counter.inc("/", http.StatusOK)
	})
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		fmt.Fprintln(w, "ok")
	})
	mux.Handle("GET /metrics", counter)
	return mux
}

func main() {
	addr := ":8080"
	if port := os.Getenv("PORT"); port != "" {
		addr = ":" + port
	}
	log.Printf("%s listening on %s", serviceName, addr)
	log.Fatal(http.ListenAndServe(addr, newMux(newRequestCounter())))
}
