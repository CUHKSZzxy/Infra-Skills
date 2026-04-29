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

### `/lmdeploy-attention-dataflow`

Use when tracing LMDeploy PyTorch attention, KV-cache, quant-policy, prefill, decode, FA3, or FlashMLA dataflow before reviewing correctness or performance changes.

### `/triton-kernel-performance`

Use when optimizing, reviewing, or validating LMDeploy PyTorch CUDA/Triton kernels for correctness and speed, especially attention, KV cache, quantization, FP8 KV cache, and Qwen3/Qwen3.5-family workloads. Includes reusable CUDA-event benchmark helpers, a generic direct-kernel microbench runner, JSONL artifact summary/compare scripts, a Qwen PyTorch pipeline smoke script, and Hopper/H100 plus LMDeploy attention/KV heuristics.

______________________________________________________________________

## Wiring locally

Link the repo skills into local agent skill directories:

```bash
scripts/link_skills.sh
```

By default this links every folder under `skills/` into both `~/.claude/skills`
and `~/.codex/skills`. Built-in Codex skills under `~/.codex/skills/.system`
are left in place.

Useful variants:

```bash
scripts/link_skills.sh claude
scripts/link_skills.sh codex
scripts/link_skills.sh copilot
scripts/link_skills.sh --dry-run
scripts/link_skills.sh --dest my-agent=/path/to/skills
```

Copilot does not have a standard local skills directory in this workspace. If
your Copilot client watches one, set `COPILOT_SKILLS_DIR` or pass a custom
`--dest`.

For Claude repo-level wiring without symlinks, add to `.claude/settings.json`
in the target repo:

```json
{
  "skillsDirectories": ["/nvme1/zhouxinyu/LMDeploy-Skills/skills"]
}
```
