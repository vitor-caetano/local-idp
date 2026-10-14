# Backstage image

The Backstage chart's default image is a demo with no plugins. The platform runs its own, built here
and pushed to the local registry.

```bash
PATH="$(brew --prefix node@24)/bin:${PATH}" ./images/backstage/build-and-push.sh
```

It scaffolds a Backstage app with `@backstage/create-app` into `backstage-app/` (gitignored), adds
the plugins below, copies in `overlay/` and `app-config.production.yaml`, builds the backend bundle
on your machine, and builds and pushes `localhost:5001/local-idp/backstage:0.1.2`. Delete
`backstage-app/` to rescaffold from scratch.

| Plugin | Side | Why |
|---|---|---|
| `@backstage/plugin-scaffolder-backend-module-gitea` | backend | `publish:gitea`, used by the golden path |
| `@backstage/plugin-kubernetes-backend` | backend | Live pods and Rollouts on a service page |
| `@backstage/plugin-kubernetes` | frontend | The Kubernetes tab |
| `@roadiehq/backstage-plugin-argo-cd` | frontend | The ArgoCD tab, over the `/argocd/api` proxy |

The app uses the new frontend system with `app.packages: all`, so both frontend plugins are
discovered and wired with no code: each ships a `./alpha` plugin that adds its own entity tab. Two
things make the tabs show data, and neither needs a rebuild:

- The Kubernetes plugin finds resources by label. The golden-path skeleton's `catalog-info.yaml` sets
  `backstage.io/kubernetes-label-selector: app=<name>`, the label its manifests carry.
- The Roadie ArgoCD tab has no filter, and its cards match every Component. The Backstage
  Application's `appConfig` (in `1-foundation/backstage/application.yaml`) limits all three to
  entities annotated `argocd/app-name`. The chart mounts it as a second `--config`, and the backend
  passes `app.extensions` to the browser at runtime.

The ArgoCD tab reads through the `/argocd/api` proxy with the read-only token the `argocd-token` Job
in `backstage-config` mints.

Bump the tag in both this script (`TAG`) and `1-foundation/backstage/application.yaml` when you
change the image, or ArgoCD keeps running the old one.
