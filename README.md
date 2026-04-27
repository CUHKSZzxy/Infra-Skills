# LMDeploy-Skills

Personal skills for LMDeploy development.

## Skills

### `/check-env`

Use when LMDeploy commands fail because the Python env, CUDA visibility, or tool invocation is wrong. Assumes the `fp8` and `vl` conda envs already exist and helps diagnose repo/env pairing, active Python, and GPU visibility.

### `/code-navigation`

Use when you need to quickly find the right LMDeploy files for a task or bug. Routes by task first, then points to likely entry files in `pytorch/`, `vl/`, `serve/`, and top-level orchestration code.

### `/support-new-model`

Use when adding support for a new LLM or VLM architecture to LMDeploy's PyTorch backend. The SKILL.md is a lean workflow with step summaries; deep content lives in `references/` and is loaded only when needed:

| Reference file                    | Load when                                                   |
| --------------------------------- | ----------------------------------------------------------- |
| `references/key-files.md`         | Before writing any code — study guide + file table          |
| `references/llm-code-skeleton.md` | Implementing Step 1 (model file) or Step 3 (config builder) |
| `references/vlm-preprocessor.md`  | Implementing Step 4 (VL preprocessor)                       |
| `references/pitfalls.md`          | Anything fails or produces wrong outputs                    |

### `/submit-pr`

Use when local LMDeploy changes are ready to become a pull request. Verifies repo state, base branch, `gh` auth, and validation first; then stages only intended files, commits, pushes, and creates the PR. Returns: PR URL, branch name, commit SHA, validation status.

### `/resolve-review`

Use when a LMDeploy pull request has review comments to address. Verifies repo state, branch, env, and `gh` auth first; then fetches comments, makes minimal fixes, validates locally, and commits/pushes only when the branch is ready. Returns: list of comments addressed, commit SHA, push confirmation.

### `/karpathy-guidelines`

Use at the start of any non-trivial implementation task to set behavioral ground rules: think before coding, minimum code, surgical edits only, define verifiable success criteria.

______________________________________________________________________

## Wiring to a repo

Add to `.claude/settings.json` in the repo:

```json
{
  "skillsDirectories": ["/nvme1/zhouxinyu/LMDeploy-Skills/skills"]
}
```
