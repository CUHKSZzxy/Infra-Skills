# LMDeploy-Skills

Personal skills for LMDeploy development.

## Skills

### `/check-env`

Use when LMDeploy commands fail because the Python env, CUDA visibility, or tool invocation is wrong. Assumes the `fp8` and `vl` conda envs already exist and helps diagnose repo/env pairing, active Python, and GPU visibility.

### `/support-new-model`

Use when adding support for a new LLM or VLM architecture to LMDeploy's PyTorch backend. The SKILL.md is a lean workflow with step summaries; deep content lives in `references/` and is loaded only when needed:

| Reference file                    | Load when                                                   |
| --------------------------------- | ----------------------------------------------------------- |
| `references/key-files.md`         | Before writing any code — study guide + file table          |
| `references/llm-code-skeleton.md` | Implementing Step 1 (model file) or Step 3 (config builder) |
| `references/vlm-preprocessor.md`  | Implementing Step 4 (VL preprocessor)                       |
| `references/pitfalls.md`          | Anything fails or produces wrong outputs                    |

### `/pr-workflow`

Use when creating, updating, reviewing, or pushing an LMDeploy pull request. Verifies repo state, branch, remote, `gh` auth, validation, staged files, and target branch before commit, push, or PR actions.

### `/karpathy-guidelines`

Use when writing, reviewing, or refactoring code to stay surgical: surface assumptions, avoid speculative features, touch only necessary lines, and define verifiable success criteria.

### `/lmdeploy-attention-dataflow`

Use when tracing LMDeploy PyTorch attention, KV-cache, quant-policy, prefill, decode, FA3, or FlashMLA dataflow before reviewing correctness or performance changes. Includes an end-to-end policy lifecycle trace from CLI/config through cache allocation, backend dispatch, kernels, and tests.

### `/triton-kernel-performance`

Use when optimizing, reviewing, or validating LMDeploy PyTorch CUDA/Triton kernels for correctness and speed, especially attention, KV cache, quantization, FP8 KV cache, and Qwen3/Qwen3.5-family workloads. Includes reusable CUDA-event benchmark helpers, a generic direct-kernel microbench runner, JSONL artifact summary/compare scripts, a Qwen PyTorch pipeline smoke script, GPU/dtype compatibility checks, and Hopper/H100 plus LMDeploy attention/KV heuristics.

______________________________________________________________________

## Wiring locally

Link the repo skills into local agent skill directories:

```bash
scripts/link_skills.sh
```

By default this links every folder under `skills/` into both `~/.claude/skills`
and `~/.codex/skills`. Built-in Codex skills under `~/.codex/skills/.system`
are left in place. Stale symlinks that point to removed skills in this repo are
pruned.

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
