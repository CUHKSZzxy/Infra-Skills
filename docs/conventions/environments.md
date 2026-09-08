# Environment Conventions

Use [machines.md](machines.md) for `WORKSPACE_ROOT`, conda paths, source
checkouts, and machine-specific env pairings.

If `import lmdeploy` raises dependency errors, report env preparation or
package drift instead of changing the checkout convention. Activate the paired
env, or use its interpreter directly for deterministic commands:

```bash
source "$CONDA_PROFILE"
conda activate <paired-env>

"$CONDA_ROOT/envs/<paired-env>/bin/python" <args>
```

For Infra-Skills documentation changes, check skill structure and references:

```bash
PYTHONDONTWRITEBYTECODE=1 "$CONDA_ROOT/envs/dev/bin/python" -m unittest discover -s tests -p test_skill_docs.py
git diff --check
```

For changed scripts, run their affected test modules. Use the full
`unittest discover -s tests` suite for shared helpers or cross-skill changes;
passing documentation checks does not establish agent behavior.

On shared storage, add `-c safe.directory="$INFRA_SKILLS_HOME"` to Git commands
when ownership requires it. Run targeted hooks only when `pre-commit` is
installed in `dev`:

```bash
"$CONDA_ROOT/envs/dev/bin/pre-commit" run --files <changed-files>
```

If pre-commit tries to use a read-only cache location, set a workspace-local
cache for that run:

```bash
PRE_COMMIT_HOME="$INFRA_SKILLS_HOME/.cache/pre-commit" \
  "$CONDA_ROOT/envs/dev/bin/pre-commit" run --files <changed-files>
```
