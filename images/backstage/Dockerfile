# ABOUTME: Host-build Dockerfile for the platform's Backstage image. Expects the create-app repo to be
# ABOUTME: built (yarn build:backend) before docker build; the image unpacks and runs the bundle.
FROM node:24-trixie-slim

ENV NODE_ENV=production
# The scaffolder backend refuses to run templates on Node 20+ without this, and every template task
# fails at its first step. The create-app Dockerfile sets it too.
ENV NODE_OPTIONS="--no-node-snapshot"

# isolated-vm (scaffolder backend) needs a toolchain for the production install.
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 g++ build-essential ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Created and owned by node before anything is copied in. A root-owned 0700 WORKDIR is untraversable
# by the node user, which fails as "Cannot find module '/app/packages/backend'" (defect class 4).
RUN mkdir -p /app && chown node:node /app && chmod 0755 /app
WORKDIR /app
USER node

# Yarn 4 config and the pinned release binary. The slim image's built-in yarn is 1.x and ignores
# yarnPath, so invoke the pinned release directly.
COPY --chown=node:node .yarnrc.yml ./
COPY --chown=node:node .yarn/releases ./.yarn/releases

COPY --chown=node:node yarn.lock package.json packages/backend/dist/skeleton.tar.gz ./
RUN tar xzf skeleton.tar.gz && rm skeleton.tar.gz

RUN --mount=type=cache,target=/home/node/.cache/yarn,uid=1000,gid=1000 \
    node .yarn/releases/yarn-*.cjs workspaces focus --all --production

COPY --chown=node:node packages/backend/dist/bundle.tar.gz app-config.yaml app-config.production.yaml ./
RUN tar xzf bundle.tar.gz && rm bundle.tar.gz

ENTRYPOINT ["node", "packages/backend"]
CMD ["--config", "app-config.production.yaml"]
