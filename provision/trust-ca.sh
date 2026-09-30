#!/usr/bin/env bash
# ABOUTME: Exports the platform's local root CA so your browser and curl trust *.localtest.me, and with
# ABOUTME: --install trusts it in your macOS login keychain (no sudo). --remove takes it out again.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

usage() {
    cat >&2 <<EOF
Usage: ${0##*/} [--install | --remove]
  (none)     export the CA to provision/local-idp-ca.crt and print how to trust it
  --install  export it and trust it in your login keychain, replacing an older one
  --remove   remove every ${CA_COMMON_NAME} from your login keychain (no cluster needed)
EOF
    exit 2
}

mode="export"
case "${1:-}" in
    "") ;;
    --install) mode="install" ;;
    --remove) mode="remove" ;;
    *) usage ;;
esac

if [[ "${mode}" == "remove" ]]; then
    untrust_ca
    exit 0
fi

require_tools kubectl base64
guard_context

OUT="${REPO_ROOT}/provision/local-idp-ca.crt"
kubectl get secret local-idp-root-ca -n cert-manager -o jsonpath='{.data.ca\.crt}' \
    | base64 -d > "${OUT}"
[[ -s "${OUT}" ]] || die "the root CA Secret is empty. Is cert-manager-issuers Healthy?"
log "Wrote ${OUT} (gitignored)."

if [[ "${mode}" == "install" ]]; then
    trust_ca "${OUT}"
    log "Done. Restart your browser to pick it up. ./provision/destroy.sh removes it again."
    exit 0
fi

cat <<EOF

Trust it in your login keychain (no sudo; macOS asks for your password):
    ${0} --install

Or system-wide (sudo):
    sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain ${OUT}

Or per command:
    curl --cacert ${OUT} https://argocd.localtest.me

./provision/destroy.sh removes it from the login keychain. A System keychain copy needs:
    sudo security delete-certificate -t -c ${CA_COMMON_NAME} /Library/Keychains/System.keychain
EOF
