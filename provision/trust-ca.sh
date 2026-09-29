#!/usr/bin/env bash
# ABOUTME: Exports the platform's local root CA so your browser and curl trust *.localtest.me.
# ABOUTME: Prints the keychain command rather than running sudo on your behalf.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

require_tools kubectl base64
guard_context

OUT="${REPO_ROOT}/provision/local-idp-ca.crt"
kubectl get secret local-idp-root-ca -n cert-manager -o jsonpath='{.data.ca\.crt}' \
    | base64 -d > "${OUT}"
[[ -s "${OUT}" ]] || die "the root CA Secret is empty. Is cert-manager-issuers Healthy?"

cat <<EOF
Wrote ${OUT} (gitignored).

Trust it system-wide on macOS (asks for your password):
    sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain ${OUT}

Or per command:
    curl --cacert ${OUT} https://argocd.localtest.me

Remove it again after ./provision/destroy.sh:
    sudo security delete-certificate -c local-idp-root-ca /Library/Keychains/System.keychain
EOF
