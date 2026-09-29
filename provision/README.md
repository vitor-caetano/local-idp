# Provision

Scripts that create, bootstrap and destroy the local cluster. Every script sources `lib.sh`, uses
`~/.kube/local-idp` as its kubeconfig, and refuses to act unless the context is `kind-local-idp`.

| Script | What it does |
|---|---|
| `create-cluster.sh` | Checks the Docker VM size, starts `kind-registry`, creates the Kind cluster from `kind-config.yaml`, maps `localhost:5001` on every node, and publishes the registry ConfigMap |
| `set-git-source.sh gitea` | Fills `REPLACE_WITH_*` in `platform/` with the in-cluster Gitea URLs and commits |
| `set-git-source.sh github <url>` | Points `platform/` at a GitHub repo instead, and commits |
| `bootstrap-argocd.sh` | Helm-installs ArgoCD at the pinned version with `platform/0-bootstrap/argocd-values.yaml` |
| `seed-gitea.sh` | Installs Gitea, derives its seed credentials, pushes your tree (Gitea mode), applies the foundation root |
| `push-to-cluster.sh` | Pushes your latest commit to the in-cluster Gitea through a port-forward |
| `trust-ca.sh` | Exports the local root CA and prints the command to trust it |
| `destroy.sh [--keep-registry]` | Deletes the cluster and the registry. `--keep-registry` keeps built images for the next run |

## Order

```bash
./provision/create-cluster.sh
cp -a solution/platform/. platform/          # or let the agent build it
./provision/set-git-source.sh gitea
./provision/bootstrap-argocd.sh
./images/backstage/build-and-push.sh         # before seeding: Backstage is wave 5
./provision/seed-gitea.sh
```

## Cost

None. Everything runs in the Rancher Desktop VM. Stop the VM, or run `destroy.sh`, to get the memory
back.
