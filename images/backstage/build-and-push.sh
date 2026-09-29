#!/usr/bin/env bash
# ABOUTME: Scaffolds the Backstage app, overlays this platform's config and plugins, builds the
# ABOUTME: backend bundle, and pushes the image to the local registry at localhost:5001.
set -euo pipefail

# The scaffold pins yarn 4 via Corepack; let it download non-interactively.
export COREPACK_ENABLE_DOWNLOAD_PROMPT=0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
readonly APP_DIR="${SCRIPT_DIR}/backstage-app"   # generated, gitignored
readonly REGISTRY="localhost:5001"
readonly IMAGE_REPO="local-idp/backstage"

# Must match backstage.image.tag in solution/platform/1-foundation/backstage/application.yaml.
TAG="${TAG:-0.1.0}"
# create-app version that ships the pinned Backstage line (components.yaml: 1.51.x).
CREATE_APP_VERSION="${CREATE_APP_VERSION:-latest}"

log() { printf '%s\n' "$*" >&2; }

require_tools() {
    local t missing=0
    for t in node yarn npx docker curl; do
        command -v "${t}" >/dev/null 2>&1 || { log "missing tool: ${t}"; missing=1; }
    done
    [[ "${missing}" -eq 0 ]] || exit 1

    # isolated-vm (scaffolder backend) fails to compile on Node 25+. Build under Node 24.
    local node_major
    node_major="$(node -p 'process.versions.node.split(".")[0]')"
    if [[ "${node_major}" -ge 25 ]]; then
        log "node ${node_major} is too new: isolated-vm fails to build. Use Node 24, e.g.:"
        log "  PATH=\"\$(brew --prefix node@24)/bin:\${PATH}\" ${0##*/}"
        exit 1
    fi

    curl -fsS "http://${REGISTRY}/v2/" >/dev/null \
        || { log "the registry at ${REGISTRY} is not answering. Run ./provision/create-cluster.sh first."; exit 1; }
}

scaffold() {
    if [[ -d "${APP_DIR}" ]]; then
        log "reusing existing scaffold at ${APP_DIR}"
        return
    fi
    log "scaffolding Backstage app (create-app ${CREATE_APP_VERSION})"
    # create-app takes the app name only from a prompt, so feed it on stdin.
    printf 'backstage\n' | npx "@backstage/create-app@${CREATE_APP_VERSION}" \
        --path "${APP_DIR}" --skip-install
}

add_plugins() {
    log "adding plugins"
    yarn --cwd "${APP_DIR}" workspace backend add \
        @backstage/plugin-scaffolder-backend-module-gitea \
        @backstage/plugin-kubernetes-backend \
        pg
    yarn --cwd "${APP_DIR}" workspace app add \
        @roadiehq/backstage-plugin-argo-cd \
        @backstage/plugin-kubernetes
}

overlay() {
    log "applying overlay (backend index + config)"
    cp -f "${SCRIPT_DIR}/overlay/packages/backend/src/index.ts" \
          "${APP_DIR}/packages/backend/src/index.ts"
    cp -f "${SCRIPT_DIR}/app-config.production.yaml" "${APP_DIR}/app-config.production.yaml"
}

build_bundle() {
    log "installing and building the backend bundle"
    yarn --cwd "${APP_DIR}" install
    yarn --cwd "${APP_DIR}" tsc
    yarn --cwd "${APP_DIR}" build:backend
}

build_image() {
    local image="${REGISTRY}/${IMAGE_REPO}:${TAG}"
    log "building ${image}"
    # Kind nodes run the host architecture (arm64 on Apple silicon), so a native build is right.
    docker build -t "${image}" -f "${SCRIPT_DIR}/Dockerfile" "${APP_DIR}"
    log "pushing ${image}"
    docker push "${image}"
    log "done: ${image}"
}

main() {
    require_tools
    scaffold
    add_plugins
    overlay
    build_bundle
    build_image
}

main "$@"
