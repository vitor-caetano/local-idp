# ABOUTME: Enforces the mechanical half of the writing standards in AGENTS.md on every tracked doc:
# ABOUTME: no em or en dashes, none of the banned words.
import glob
import os
import re

from conftest import REPO_ROOT

BANNED = [
    "delve", "leverage", "robust", "seamless", "comprehensive", "under the hood",
    "navigate complexities", "genuinely", "in today's landscape",
]
SKIP_DIRS = {".git", ".venv", "backstage-app", "node_modules", ".pytest_cache"}


def _docs():
    for path in glob.glob(os.path.join(REPO_ROOT, "**", "*.md"), recursive=True):
        if not set(os.path.relpath(path, REPO_ROOT).split(os.sep)) & SKIP_DIRS:
            yield path


def test_no_em_or_en_dashes():
    offenders = []
    for path in _docs():
        with open(path, encoding="utf-8") as handle:
            for lineno, line in enumerate(handle, 1):
                if "—" in line or "–" in line:
                    offenders.append(f"{os.path.relpath(path, REPO_ROOT)}:{lineno}")
    assert not offenders, "em or en dash in: " + ", ".join(offenders)


def test_no_banned_words():
    offenders = []
    pattern = re.compile(r"\b(" + "|".join(re.escape(w) for w in BANNED) + r")\b", re.IGNORECASE)
    for path in _docs():
        rel = os.path.relpath(path, REPO_ROOT)
        # AGENTS.md lists the banned words in order to ban them.
        if rel == "AGENTS.md":
            continue
        with open(path, encoding="utf-8") as handle:
            for lineno, line in enumerate(handle, 1):
                if match := pattern.search(line):
                    offenders.append(f"{rel}:{lineno}: {match.group(0)}")
    assert not offenders, "\n".join(offenders)
