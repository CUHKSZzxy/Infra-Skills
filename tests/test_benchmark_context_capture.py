import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CAPTURE_SCRIPT = REPO_ROOT / "scripts" / "capture_deployment_context.sh"


class BenchmarkContextCaptureTest(unittest.TestCase):

    def test_capture_context_writes_deployment_space_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            run_dir = tmp_path / "run"
            config_path = tmp_path / "config.sh"
            config_path.write_text(
                "\n".join(
                    [
                        "MODEL_PATH=/models/qwen35",
                        "MODEL_ABBR=qwen35",
                        "BACKEND=pytorch",
                        "DEPLOYMENT_ARCHITECTURE=colocated",
                        "TENSOR_PARALLEL_SIZE=2",
                        "DATA_PARALLEL_SIZE=1",
                        "DATASET_NAME=sharegpt",
                        "WORKLOAD_PRESET=custom",
                        "OUT_LENS=(None 2048)",
                        "NUM_PROMPTS=(4 8)",
                        "SLO_MAX_MEAN_TTFT_MS=2000",
                    ]
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [str(CAPTURE_SCRIPT), str(run_dir), str(REPO_ROOT), str(config_path)],
                check=False,
                capture_output=True,
                text=True,
            )

            context_dir = run_dir / "context"
            context_md = context_dir / "deployment_context.md"

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(context_md.exists())
            self.assertTrue((context_dir / "git.txt").exists())
            self.assertTrue((context_dir / "python.txt").exists())
            self.assertTrue((context_dir / "gpu.txt").exists())
            self.assertTrue((context_dir / "config.sh.snapshot").exists())
            self.assertTrue((context_dir / "commands" / "README.md").exists())

            text = context_md.read_text(encoding="utf-8")
            self.assertIn("## Serving Scenario", text)
            self.assertIn("## Serving Topology And Parallelism", text)
            self.assertIn("qwen35", text)
            self.assertIn("TENSOR_PARALLEL_SIZE", text)
            self.assertIn("SLO_MAX_MEAN_TTFT_MS", text)


if __name__ == "__main__":
    unittest.main()
