# What is not included

Left out on purpose, so a reference that looks missing has an answer.

| Not here | Why |
|---|---|
| Any AI component (kgateway, agentgateway, kagent, KServe, vLLM, llm-d, LLM Guard, MCP) | Out of scope by design (D2). The sibling EKS platform has them. |
| A cloud provider, Terraform, IAM, cloud load balancers, EBS | Kind replaces them (D1). |
| Vendored Helm charts | Pulled from upstream at pinned versions (D5). |
| High availability for anything | One replica of everything, sized for a laptop. |
| Durable secrets | OpenBao runs in dev mode, in memory. A restart empties it; ExternalSecrets keep what they already wrote. |
| Trace persistence | Tempo has no volume. A restart empties the trace store. |
| Real authentication | Backstage uses guest sign-in and Argo Workflows uses server auth mode. Both are wrong for anything shared. |
| A Rollouts traffic router | The canary weight is the share of pods, not of requests. Adding the Gateway API plugin would split traffic precisely. |
| Tracing in the golden-path service | It uses only the standard library. Add the OpenTelemetry Go SDK and point it at `opentelemetry-collector.observability.svc:4317` when you want spans. |
| Frontend wiring for the ArgoCD and Kubernetes tabs in Backstage | The plugins are installed; the entity page wiring depends on the Backstage frontend-system release. See `images/backstage/README.md`. |
