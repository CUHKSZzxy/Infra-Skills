from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "skills" / "optimize-kernel" / "scripts"
CAMPAIGN = SCRIPTS / "kernel_campaign.py"
CASE_TEMPLATE = SCRIPTS / "microbench_case_template.py"


def load_script(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class OptimizeKernelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.campaign_utils = load_script(
            "kernel_campaign_utils_test",
            "kernel_campaign_utils.py",
        )
        cls.compare = load_script(
            "compare_kernel_bench_test",
            "compare_kernel_bench.py",
        )
        cls.summarize = load_script(
            "summarize_kernel_bench_test",
            "summarize_kernel_bench.py",
        )
        cls.runner = load_script(
            "kernel_microbench_test",
            "kernel_microbench.py",
        )

    def test_paired_decision_requires_correctness_and_material_gain(self):
        rows = [
            {
                "type": "paired_bench",
                "name": "decode-short",
                "correct": True,
                "required": True,
                "headline": True,
                "speedup": 1.10,
                "delta_pct": -9.09,
            },
            {
                "type": "paired_bench",
                "name": "decode-long",
                "correct": True,
                "required": True,
                "headline": True,
                "speedup": 1.06,
                "delta_pct": -5.66,
            },
        ]

        decision = self.campaign_utils.decide_paired_results(
            rows,
            minimum_gain_pct=3.0,
            regression_pct=3.0,
        )
        self.assertEqual(decision["status"], "accepted")
        self.assertGreater(decision["gain_pct"], 3.0)

        rows[1]["correct"] = False
        decision = self.campaign_utils.decide_paired_results(
            rows,
            minimum_gain_pct=3.0,
            regression_pct=3.0,
        )
        self.assertEqual(decision["status"], "rejected")
        self.assertEqual(decision["correctness_failures"], ["decode-long"])

    def test_workload_manifest_is_frozen(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "workloads.json"
            original = self.campaign_utils.workload_manifest(
                [{"name": "decode", "shape": "q=1,kv=4096"}]
            )
            changed = self.campaign_utils.workload_manifest(
                [{"name": "decode", "shape": "q=1,kv=8192"}]
            )
            self.campaign_utils.freeze_workload_manifest(path, original)
            self.campaign_utils.freeze_workload_manifest(path, original)
            with self.assertRaisesRegex(RuntimeError, "manifest changed"):
                self.campaign_utils.freeze_workload_manifest(path, changed)

    def test_legacy_comparison_uses_median_across_runs(self):
        rows = [
            {"name": "kernel", "shape": "x", "dtype": "fp16", "mean_ms": 1.0},
            {"name": "kernel", "shape": "x", "dtype": "fp16", "mean_ms": 10.0},
            {"name": "kernel", "shape": "x", "dtype": "fp16", "mean_ms": 7.0},
        ]
        aggregated = self.compare.aggregate_by_key(rows)
        row = aggregated[("kernel", "x", "fp16")]
        self.assertEqual(row["median_ms"], 7.0)
        self.assertEqual(row["run_count"], 3)

    def test_summarizer_expands_paired_rows(self):
        paired = {
            "type": "paired_bench",
            "name": "kernel",
            "shape": "x",
            "dtype": "fp16",
            "correct": True,
            "speedup": 1.2,
            "baseline": {"mean_ms": 1.2, "median_ms": 1.2},
            "candidate": {"mean_ms": 1.0, "median_ms": 1.0},
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "results.jsonl"
            path.write_text(json.dumps(paired) + "\n", encoding="utf-8")
            rows = self.summarize.iter_rows(path)

        self.assertEqual(len(rows), 2)
        self.assertEqual(
            [row["metadata"]["variant"] for row in rows],
            ["baseline", "candidate"],
        )
        self.assertEqual(rows[1]["metadata"]["speedup"], 1.2)

    def test_campaign_init_records_a_bounded_single_gpu_contract(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "campaign"
            case_file = Path(temp_dir) / "case.py"
            case_file.write_bytes(CASE_TEMPLATE.read_bytes())
            completed = subprocess.run(
                [
                    sys.executable,
                    str(CAMPAIGN),
                    "init",
                    str(root),
                    "--case-file",
                    str(case_file),
                    "--source-checkout",
                    str(REPO_ROOT),
                    "--python",
                    sys.executable,
                    "--gpu",
                    "0",
                    "--max-rounds",
                    "3",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            config = json.loads((root / "campaign.json").read_text(encoding="utf-8"))
            checkpoint = json.loads(
                (root / "checkpoint.json").read_text(encoding="utf-8")
            )
            case_file.write_text("# changed\n", encoding="utf-8")
            resumed = subprocess.run(
                [
                    sys.executable,
                    str(CAMPAIGN),
                    "run",
                    str(root),
                    "--hypothesis",
                    "must not run with a changed contract",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(config["gpu"], "0")
        self.assertEqual(config["max_rounds"], 3)
        self.assertEqual(
            config["case_file_sha256"],
            hashlib.sha256(CASE_TEMPLATE.read_bytes()).hexdigest(),
        )
        self.assertEqual(checkpoint["status"], "active")
        self.assertEqual(checkpoint["next_round"], 0)
        self.assertNotEqual(resumed.returncode, 0)
        self.assertIn("benchmark case file changed", resumed.stderr)

    def test_campaign_records_runner_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "campaign"
            case_file = Path(temp_dir) / "broken_case.py"
            case_file.write_text(
                "def build_cases(args):\n    raise RuntimeError('broken case')\n",
                encoding="utf-8",
            )
            init = subprocess.run(
                [
                    sys.executable,
                    str(CAMPAIGN),
                    "init",
                    str(root),
                    "--case-file",
                    str(case_file),
                    "--source-checkout",
                    str(REPO_ROOT),
                    "--python",
                    sys.executable,
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(init.returncode, 0, init.stderr)

            run = subprocess.run(
                [
                    sys.executable,
                    str(CAMPAIGN),
                    "run",
                    str(root),
                    "--hypothesis",
                    "exercise runner failure",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            checkpoint = json.loads(
                (root / "checkpoint.json").read_text(encoding="utf-8")
            )

        self.assertNotEqual(run.returncode, 0)
        self.assertEqual(checkpoint["last_decision"]["status"], "runner_failed")
        self.assertEqual(checkpoint["status"], "active")

    def test_microbench_profile_mode_launches_only_selected_variant(self):
        events = []

        class FakeCuda:
            @staticmethod
            def synchronize():
                events.append("sync")

        class FakeTorch:
            cuda = FakeCuda()

        pair = self.runner.BenchmarkPair(
            name="kernel",
            baseline=lambda: events.append("baseline"),
            candidate=lambda: events.append("candidate"),
            before=lambda: events.append("before"),
            after=lambda: events.append("after"),
            shape="q=1,kv=4096",
            dtype="fp16",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir) / "profile.jsonl"
            with redirect_stdout(io.StringIO()):
                self.runner._run_profile_launch(
                    cases=[pair],
                    variant="candidate",
                    warmup=2,
                    out=out,
                    label="ncu",
                    torch=FakeTorch(),
                )
            row = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(
            events,
            [
                "before",
                "candidate",
                "candidate",
                "sync",
                "candidate",
                "sync",
                "after",
            ],
        )
        self.assertEqual(row["type"], "profile_launch")
        self.assertEqual(row["variant"], "candidate")
        self.assertEqual(row["warmup"], 2)


if __name__ == "__main__":
    unittest.main()
