# Backstage image

The Backstage chart's default image is a demo with no plugins. The platform runs its own, built here
and pushed to the local registry.

```bash
PATH="$(brew --prefix node@24)/bin:${PATH}" ./images/backstage/build-and-push.sh
```

It scaffolds a Backstage app with `@backstage/create-app` into `backstage-app/` (gitignored), adds
the plugins below, copies in `overlay/` and `app-config.production.yaml`, builds the backend bundle
on your machine, and builds and pushes `localhost:5001/local-idp/backstage:0.1.1`. Delete
`backstage-app/` to rescaffold from scratch.

| Plugin | Side | Why |
|---|---|---|
| `@backstage/plugin-scaffolder-backend-module-gitea` | backend | `publish:gitea`, used by the golden path |
| `@backstage/plugin-kubernetes-backend` | backend | Live pods and Rollouts on a service page |
| `@backstage/plugin-kubernetes` | frontend | The Kubernetes tab |
| `@roadiehq/backstage-plugin-argo-cd` | frontend | The ArgoCD tab, over the `/argocd/api` proxy |

The two frontend plugins are installed but not wired into the entity page, because that wiring
changes with each Backstage frontend-system release. Add the tabs to
`packages/app/src/components/catalog/EntityPage.tsx` (or the new frontend system's equivalent) in
`backstage-app/`, then rebuild. The catalog, the scaffolder and the golden path work without them.

Bump the tag in both this script (`TAG`) and `1-foundation/backstage/application.yaml` when you
change the image, or ArgoCD keeps running the old one.
