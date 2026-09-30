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
# The pinned Backstage release (components.yaml: backstage app_version), the create-app version that
# ships it, and the plugin versions from the same release manifest.
readonly BACKSTAGE_RELEASE="1.51.2"
readonly BACKSTAGE_MANIFEST_URL="https://versions.backstage.io/v1/releases/${BACKSTAGE_RELEASE}/manifest.json"
CREATE_APP_VERSION="${CREATE_APP_VERSION:-0.8.3}"
readonly SCAFFOLDER_GITEA_VERSION="0.2.21"
readonly KUBERNETES_BACKEND_VERSION="0.21.4"
readonly KUBERNETES_VERSION="0.12.19"
# Outside the Backstage release manifest. The scaffold's npmMinimalAgeGate (3d) refuses anything
# fresher, so pin a release that has aged past it.
readonly ROADIE_ARGO_CD_VERSION="2.12.5"
readonly PG_VERSION="8.23.0"
# Transitive, pinned below 4.9.2. See pin_release().
readonly YARNPKG_CORE_VERSION="4.9.1"

log() { printf '%s\n' "$*" >&2; }

# Corepack picks the yarn version from the directory yarn starts in, not from --cwd. Started from the
# repo root it runs yarn 1, which rewrites the scaffold's yarn 4 lockfile in the v1 format. Start it
# inside the app so the scaffold's packageManager pin applies.
app_yarn() { (cd "${APP_DIR}" && yarn "$@"); }

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

    pin_release
}

# The scaffold's package.json uses caret ranges, and its lockfile does not cover them, so yarn
# resolves every ^1.x @backstage package to the newest 1.x. That mixes releases: one tsc run found
# frontend-plugin-api 0.13, 0.17 and 0.18 in the same tree (TS2742). Pinning every @backstage
# package to the release manifest through resolutions is what makes the build that release.
#
# @yarnpkg/core rides along: 4.9.2 (2026-09-24) was published with a dependency on
# patch:got@...#~/.yarn/patches/got-npm-11.8.2-*.patch, a file that exists only in Yarn's own repo,
# so every install that resolves it fails with ENOENT. 4.9.1 depends on plain got.
pin_release() {
    log "pinning @backstage packages to release ${BACKSTAGE_RELEASE}"
    node -e '
        const fs = require("fs");
        const [appDir, manifestUrl, yarnpkgCore] = process.argv.slice(1);
        fetch(manifestUrl)
            .then((r) => { if (!r.ok) throw new Error(manifestUrl + ": " + r.status); return r.json(); })
            .then((manifest) => {
                const path = appDir + "/package.json";
                const pkg = JSON.parse(fs.readFileSync(path, "utf8"));
                const resolutions = { ...pkg.resolutions, "@yarnpkg/core": yarnpkgCore };
                for (const { name, version } of manifest.packages) resolutions[name] = version;
                pkg.resolutions = resolutions;
                fs.writeFileSync(path, JSON.stringify(pkg, null, 2) + "\n");
            })
            .catch((e) => { console.error(e.message); process.exit(1); });
    ' "${APP_DIR}" "${BACKSTAGE_MANIFEST_URL}" "${YARNPKG_CORE_VERSION}"
}

add_plugins() {
    log "adding plugins"
    app_yarn workspace backend add \
        "@backstage/plugin-scaffolder-backend-module-gitea@${SCAFFOLDER_GITEA_VERSION}" \
        "@backstage/plugin-kubernetes-backend@${KUBERNETES_BACKEND_VERSION}" \
        "pg@${PG_VERSION}"
    app_yarn workspace app add \
        "@roadiehq/backstage-plugin-argo-cd@${ROADIE_ARGO_CD_VERSION}" \
        "@backstage/plugin-kubernetes@${KUBERNETES_VERSION}"
}

overlay() {
    log "applying overlay (backend index + config)"
    cp -f "${SCRIPT_DIR}/overlay/packages/backend/src/index.ts" \
          "${APP_DIR}/packages/backend/src/index.ts"
    cp -f "${SCRIPT_DIR}/app-config.production.yaml" "${APP_DIR}/app-config.production.yaml"
}

build_bundle() {
    log "installing and building the backend bundle"
    app_yarn install
    app_yarn tsc
    app_yarn build:backend
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
