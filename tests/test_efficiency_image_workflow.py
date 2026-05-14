import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "skills" / "e2e-efficiency-benchmark" / "scripts"


class EfficiencyImageWorkflowTest(unittest.TestCase):

    def test_bench_image_dry_run_builds_chat_image_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = tmp_path / "config.sh"
            profile_path = tmp_path / "profile_restful_api.py"
            profile_path.write_text("# benchmark client placeholder\n", encoding="utf-8")
            config_path.write_text(
                "\n".join(
                    [
                        "MODEL_PATH=/models/qwen35-35b-a3b",
                        "MODEL_ABBR=qwen35_35b_a3b",
                        "PORT=18035",
                        "TENSOR_PARALLEL_SIZE=2",
                        "DATA_PARALLEL_SIZE=1",
                        "QUANT_POLICY=0",
                        "PROFILE_RESTFUL_API=" + str(profile_path),
                        "PYTHON_BIN=python3",
                        "BENCH_LOG_DIR=0_bench_logs",
                        "IMAGE_WORKLOAD_PRESET=custom",
                        "IMAGE_INPUT_LENS=(64)",
                        "IMAGE_OUTPUT_LENS=(32)",
                        "IMAGE_NUM_PROMPTS=(3)",
                        "IMAGE_RESOLUTIONS=(360p)",
                        "IMAGE_COUNTS=(1)",
                        "IMAGE_FORMAT=jpeg",
                        "IMAGE_CONTENT=blank",
                        "IMAGE_RANGE_RATIO=1",
                        "IMAGE_BENCH_DRY_RUN=1",
                    ]
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [str(SCRIPT_DIR / "bench_image.sh"), str(config_path), "baseline"],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--backend lmdeploy-chat", result.stdout)
        self.assertIn("--dataset-name image", result.stdout)
        self.assertIn("--random-input-len 64", result.stdout)
        self.assertIn("--random-output-len 32", result.stdout)
        self.assertIn("--image-resolution 360p", result.stdout)
        self.assertIn("--image-count 1", result.stdout)
        self.assertNotIn("--dataset-path", result.stdout)


if __name__ == "__main__":
    unittest.main()
