# Built in the cluster by the ci-go-service WorkflowTemplate with rootless BuildKit.
FROM golang:1.27.0 AS build
WORKDIR /src
COPY go.mod ./
COPY *.go ./
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/service .

# A static binary needs nothing else. The numeric user is what runAsNonRoot can verify.
FROM scratch
COPY --from=build /out/service /service
USER 65532:65532
EXPOSE 8080
ENTRYPOINT ["/service"]
