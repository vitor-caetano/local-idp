# ABOUTME: set-git-source.sh fills the placeholders, switches Gitea to GitHub and back, and leaves no
# ABOUTME: Application behind. Runs the real script against a throwaway copy of the repo.
import os
import shutil
import subprocess

import pytest

yaml = pytest.importorskip("yaml")

from conftest import REPO_ROOT, SOLUTION

GITEA_URL = "http://gitea-http.gitea.svc:3000/platform/local-idp.git"
GITEA_RAW = "http://gitea-http.gitea.svc:3000/platform/local-idp/raw/branch/main"
GITHUB_URL = "https://github.com/example/local-idp.git"
GITHUB_RAW = "https://raw.githubusercontent.com/example/local-idp/main"


@pytest.fixture
def repo(tmp_path):
    for tool in ("git", "perl", "bash"):
        if shutil.which(tool) is None:
            pytest.skip(f"{tool} not available")
    shutil.copytree(os.path.join(REPO_ROOT, "provision"), tmp_path / "provision")
    shutil.copytree(SOLUTION, tmp_path / "platform")
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True, env=env)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, env=env)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=tmp_path, check=True, env=env)
    return tmp_path, env


def _switch(repo, *args):
    path, env = repo
    return subprocess.run(["bash", str(path / "provision" / "set-git-source.sh"), *args],
                          cwd=path, capture_output=True, text=True, env=env)


def _repo_urls(path):
    urls = set()
    for root, _, files in os.walk(path / "platform"):
        for name in files:
            if name != "application.yaml" and not root.endswith("0-bootstrap"):
                continue
            if not name.endswith(".yaml"):
                continue
            with open(os.path.join(root, name)) as handle:
                for doc in yaml.safe_load_all(handle):
                    if isinstance(doc, dict) and doc.get("kind") == "Application":
                        source = doc["spec"]["source"]
                        if "chart" not in source:
                            urls.add(source["repoURL"])
    return urls


def _grep(path, needle):
    """YAML files under platform/ that contain needle. READMEs name the placeholders on purpose."""
    hits = []
    for root, _, files in os.walk(path / "platform"):
        for name in files:
            if not name.endswith((".yaml", ".yml")):
                continue
            with open(os.path.join(root, name), errors="ignore") as handle:
                if needle in handle.read():
                    hits.append(name)
    return hits


def test_gitea_then_github_then_gitea(repo):
    path, _ = repo

    res = _switch(repo, "gitea")
    assert res.returncode == 0, res.stderr
    assert _repo_urls(path) == {GITEA_URL}
    assert not _grep(path, "REPLACE_WITH_")
    assert _grep(path, GITEA_RAW)

    res = _switch(repo, "github", "https://github.com/example/local-idp")
    assert res.returncode == 0, res.stderr
    assert _repo_urls(path) == {GITHUB_URL}
    assert _grep(path, GITHUB_RAW)
    assert not _grep(path, GITEA_URL)

    res = _switch(repo, "gitea")
    assert res.returncode == 0, res.stderr
    assert _repo_urls(path) == {GITEA_URL}
    assert not _grep(path, "github.com")


def test_every_switch_is_a_commit(repo):
    path, env = repo
    _switch(repo, "gitea")
    log = subprocess.run(["git", "log", "--oneline"], cwd=path, capture_output=True, text=True,
                         env=env).stdout
    assert "Point the platform at gitea" in log
    status = subprocess.run(["git", "status", "--porcelain"], cwd=path, capture_output=True,
                            text=True, env=env).stdout
    assert status == "", f"switch left uncommitted changes:\n{status}"


def test_rejects_a_non_github_url(repo):
    assert _switch(repo, "github", "https://gitlab.com/example/local-idp").returncode != 0


def test_services_repos_are_not_rewritten(repo):
    # The golden-path AppProject names the Gitea services org, which lives in Gitea in every mode.
    path, _ = repo
    _switch(repo, "github", "https://github.com/example/local-idp")
    assert _grep(path, "http://gitea-http.gitea.svc:3000/services/*")
