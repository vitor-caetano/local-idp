# Two stages: build a static binary, then copy it into distroless nonroot. The runtime image has no
# shell and runs as uid 65532, which the Rollout pins as a numeric runAsUser.
FROM golang:1.27.0 AS build
WORKDIR /src
COPY go.mod ./
COPY *.go ./
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/app .

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /out/app /app
USER 65532:65532
EXPOSE 8080
ENTRYPOINT ["/app"]
