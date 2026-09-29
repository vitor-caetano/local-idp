#!/usr/bin/env bash
# ABOUTME: Points every platform Application at one Git source, the in-cluster Gitea or GitHub,
# ABOUTME: by rewriting repoURL and the Backstage catalog base across platform/, then commits.
#
# Usage:
#   ./provision/set-git-source.sh gitea
#   ./provision/set-git-source.sh github https://github.com/<owner>/<repo>.git
#
# Two values change together:
#   REPLACE_WITH_PLATFORM_REPO_URL  the repoURL of every Git-sourced Application
#   REPLACE_WITH_PLATFORM_RAW_BASE  where Backstage reads the golden-path template and org file
#
# The first run replaces the placeholders. Later runs replace whatever the previous run wrote, read
# back from root-app.yaml and the Backstage Application, so you can switch back and forth. Gitea
# stays installed either way: the golden-path service repos and their webhooks always live there.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

require_tools git perl

PLATFORM="${REPO_ROOT}/platform"
ROOT_APP="${PLATFORM}/0-bootstrap/root-app.yaml"
BACKSTAGE_APP="${PLATFORM}/1-foundation/backstage/application.yaml"

[[ -f "${ROOT_APP}" && -f "${BACKSTAGE_APP}" ]] \
    || die "platform/ is missing or incomplete. Create it first: cp -a solution/platform/. platform/"

mode="${1:-}"
case "${mode}" in
    gitea)
        new_url="${GITEA_INTERNAL_URL}/${GITEA_ORG}/${GITEA_REPO}.git"
        new_raw="${GITEA_INTERNAL_URL}/${GITEA_ORG}/${GITEA_REPO}/raw/branch/main"
        ;;
    github)
        url="${2:-}"
        [[ "${url}" =~ ^https://github\.com/([^/]+)/([^/]+)$ ]] \
            || die "usage: $0 github https://github.com/<owner>/<repo>.git"
        owner="${BASH_REMATCH[1]}"
        repo="${BASH_REMATCH[2]%.git}"
        new_url="https://github.com/${owner}/${repo}.git"
        new_raw="https://raw.githubusercontent.com/${owner}/${repo}/main"
        ;;
    *)
        die "usage: $0 gitea | github https://github.com/<owner>/<repo>.git"
        ;;
esac

# The current values, whatever they are: placeholders on the first run, a URL afterwards.
old_url="$(sed -n 's/^ *repoURL: *//p' "${ROOT_APP}" | head -1)"
old_raw="$(grep -A1 'name: PLATFORM_RAW_BASE' "${BACKSTAGE_APP}" | sed -n 's/^ *value: *"\{0,1\}\([^"]*\)"\{0,1\}$/\1/p' | head -1)"
[[ -n "${old_url}" && -n "${old_raw}" ]] || die "could not read the current Git source from platform/"

if [[ "${old_url}" == "${new_url}" && "${old_raw}" == "${new_raw}" ]]; then
    log "platform/ already points at ${new_url}"
    exit 0
fi

log "repoURL:  ${old_url}  ->  ${new_url}"
log "raw base: ${old_raw}  ->  ${new_raw}"

# perl rather than sed -i, which differs between BSD and GNU. \Q...\E quotes the old value, so the
# dots and slashes in a URL are literal.
export OLD_URL="${old_url}" NEW_URL="${new_url}" OLD_RAW="${old_raw}" NEW_RAW="${new_raw}"
find "${PLATFORM}" -type f \( -name '*.yaml' -o -name '*.yml' \) -print0 \
    | xargs -0 perl -pi -e 's/\Q$ENV{OLD_URL}\E/$ENV{NEW_URL}/g; s/\Q$ENV{OLD_RAW}\E/$ENV{NEW_RAW}/g'

if grep -rq --include='*.yaml' --include='*.yml' 'REPLACE_WITH_' "${PLATFORM}"; then
    grep -rn --include='*.yaml' --include='*.yml' 'REPLACE_WITH_' "${PLATFORM}" >&2
    die "placeholders remain under platform/ after the switch"
fi

git -C "${REPO_ROOT}" add platform
if git -C "${REPO_ROOT}" diff --cached --quiet; then
    log "nothing to commit"
else
    git -C "${REPO_ROOT}" commit -q -m "Point the platform at ${mode}: ${new_url}"
    log "committed. Push it where ArgoCD reads:"
    if [[ "${mode}" == "gitea" ]]; then
        log "  ./provision/push-to-cluster.sh   (or ./provision/seed-gitea.sh on a fresh cluster)"
    else
        log "  git push <your-github-remote> main"
        log "then re-apply the plane roots so ArgoCD re-reads them from GitHub:"
        log "  kubectl apply -n argocd -f platform/0-bootstrap/root-app.yaml"
        log "  kubectl apply -n argocd -f platform/0-bootstrap/self-service-app.yaml   (if phase 6 is done)"
    fi
fi
