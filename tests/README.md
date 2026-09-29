# Tests

Two kinds, one suite.

**Cluster-free** tests read the reference build under `solution/` and run anywhere, including CI:

| File | What it holds |
|---|---|
| `test_components.py` | Every component pinned, the lock file current, every chart Application on its pin |
| `test_platform_contract.py` | The defect classes in `AGENTS.md` that a manifest can show without a cluster |
| `test_argocd_health_checks.py` | Every shipped kind has a health decision |
| `test_policies.py` | Every Kyverno rule ships Audit and is scoped to the enrolment label |
| `test_git_source.py` | `set-git-source.sh` switches Gitea to GitHub and back, on a throwaway copy |
| `test_golden_path_template.py` | The template renders to manifests the AppProject, Gateway and policies accept, and its Go code passes `go test` |
| `test_writing_standards.py` | No dashes or banned words in any Markdown |

**Cluster-bound** tests, `test_phase_N_*.py`, are the phase gates. They skip unless both variables
are set, and abort if the current context is not the expected one:

```bash
KUBECONFIG_FILE=$HOME/.kube/local-idp EXPECTED_CONTEXT=kind-local-idp \
  uv run --group test pytest tests/test_phase_3_observability.py -v
```

Some phase tests create short-lived probe pods or Workflows and delete them afterwards. None of them
changes anything ArgoCD manages.
