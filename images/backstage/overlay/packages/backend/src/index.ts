// ABOUTME: Backstage backend entrypoint for the platform image. New backend system, plus the Gitea
// ABOUTME: scaffolder module for the golden path and the Kubernetes backend for live service state.
//
// Copied over the scaffolded packages/backend/src/index.ts by build-and-push.sh. The ArgoCD
// integration is a frontend plugin over the proxy, so it needs no backend module here.
import { createBackend } from '@backstage/backend-defaults';

const backend = createBackend();

// Core
backend.add(import('@backstage/plugin-app-backend'));
backend.add(import('@backstage/plugin-proxy-backend'));

// Catalog
backend.add(import('@backstage/plugin-catalog-backend'));
backend.add(
  import('@backstage/plugin-catalog-backend-module-scaffolder-entity-model'),
);

// Scaffolder plus the Gitea publish action the golden path uses
backend.add(import('@backstage/plugin-scaffolder-backend'));
backend.add(import('@backstage/plugin-scaffolder-backend-module-gitea'));

// Kubernetes: pods, Rollouts and events on each service's page
backend.add(import('@backstage/plugin-kubernetes-backend'));

// TechDocs
backend.add(import('@backstage/plugin-techdocs-backend'));

// Auth (guest provider for a local cluster; replace for anything shared)
backend.add(import('@backstage/plugin-auth-backend'));
backend.add(import('@backstage/plugin-auth-backend-module-guest-provider'));

// Permissions, allow-all
backend.add(import('@backstage/plugin-permission-backend'));
backend.add(
  import('@backstage/plugin-permission-backend-module-allow-all-policy'),
);

backend.start();
