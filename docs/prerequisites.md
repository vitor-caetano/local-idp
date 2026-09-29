# Prerequisites

## Docker VM

Rancher Desktop with the **dockerd (moby)** container engine. Kind needs the Docker API; the
containerd/nerdctl engine does not provide it.

Preferences, Virtual Machine: **16 GB memory, 6 CPUs**. `provision/create-cluster.sh` refuses to run
below 14 GiB or 6 CPUs, because the later phases do not fail cleanly on a small VM: pods sit Pending
or are OOMKilled while ArgoCD reports Progressing indefinitely.

Raise the inotify limits once per VM start, or pods crash with "too many open files":

```bash
rdctl shell sudo sysctl -w fs.inotify.max_user_instances=512 fs.inotify.max_user_watches=524288
```

`create-cluster.sh` checks the value and warns if it is low.

## Tools

| Tool | Why |
|---|---|
| `kind` v0.33.0 | The cluster |
| `kubectl` | Everything |
| `helm` | The ArgoCD bootstrap |
| `git`, `curl`, `perl` | The provision scripts |
| `node` 24 and `yarn` | Building the Backstage image (Node 25+ cannot build isolated-vm) |
| `uv` | Running the test suite |
| `go` 1.27 (optional) | Lets the cluster-free suite run the golden-path service's own tests |

### With Devbox (pinned)

`devbox.json` pins every tool above. Docker stays on the host (Rancher Desktop).

```bash
devbox shell        # first run installs Nix (asks for sudo) and the packages
```

Inside the shell:

- `kind` v0.33.0 comes from its GitHub release, checked against the published sha256, because
  Nixhub lags the Kind release. `scripts/install-kind.sh` puts it in `.devbox/bin`.
- `yarn` is the Corepack shim from Node 24, so the Backstage scaffold gets the yarn 4 it pins.
- `KUBECONFIG` points at `~/.kube/local-idp`, so no command falls back to `~/.kube/config`.

Scripts: `devbox run test` (cluster-free suite), `devbox run test-cluster <test file>` (sets
`KUBECONFIG_FILE` and `EXPECTED_CONTEXT`), `devbox run check-context`, `devbox run inotify`.

### With Homebrew

```bash
brew install kind kubectl helm node@24 yarn uv go
```

## Disk

About 25 GB free for images, the registry, and the local-path volumes.

## Ports

Host ports 80, 443 and 5001 on 127.0.0.1 must be free.
