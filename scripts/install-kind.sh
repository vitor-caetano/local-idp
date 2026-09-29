#!/usr/bin/env bash
# ABOUTME: Installs the pinned Kind release into .devbox/bin, verified against its published sha256.
# ABOUTME: Nixhub lags the Kind release, so devbox.json calls this from its init_hook instead.
set -euo pipefail

# components.yaml: kind app_version. Checksums from the v0.33.0 release's *.sha256sum files.
readonly KIND_VERSION="v0.33.0"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly REPO_ROOT
readonly BIN_DIR="${REPO_ROOT}/.devbox/bin"
readonly KIND_BIN="${BIN_DIR}/kind"

log() { printf '%s\n' "$*" >&2; }

if [[ -x "${KIND_BIN}" ]] && "${KIND_BIN}" version 2>/dev/null | grep -q "kind ${KIND_VERSION} "; then
    exit 0
fi

os="$(uname -s | tr '[:upper:]' '[:lower:]')"
case "$(uname -m)" in
    arm64 | aarch64) arch="arm64" ;;
    x86_64 | amd64) arch="amd64" ;;
    *) log "unsupported architecture: $(uname -m)"; exit 1 ;;
esac

case "${os}-${arch}" in
    darwin-arm64) sha="0c8c7dbe5e23594a198b786c4bc13dacc101fa6196b0cb0b23a1ca44e61f4b4f" ;;
    darwin-amd64) sha="5a99f26f57246dc9319dd294803313197a0f34d33c525b3ea8b655db5916ece0" ;;
    linux-amd64) sha="aee6151561422756b764a4ae28e7f44cda5af5a9eead3cc9985112b1de8d8e0d" ;;
    linux-arm64) sha="20022bee6cfcd5086cb7234d218e3454e6090022f2a8f55d1fa7fcf42c3867a2" ;;
    *) log "unsupported platform: ${os}-${arch}"; exit 1 ;;
esac

log "installing kind ${KIND_VERSION} (${os}-${arch}) into ${BIN_DIR}"
mkdir -p "${BIN_DIR}"
tmp="$(mktemp)"
trap 'rm -f "${tmp}"' EXIT
curl -fsSL -o "${tmp}" \
    "https://github.com/kubernetes-sigs/kind/releases/download/${KIND_VERSION}/kind-${os}-${arch}"
echo "${sha}  ${tmp}" | shasum -a 256 -c - >/dev/null \
    || { log "kind checksum mismatch; refusing to install"; exit 1; }
chmod +x "${tmp}"
mv "${tmp}" "${KIND_BIN}"
trap - EXIT
