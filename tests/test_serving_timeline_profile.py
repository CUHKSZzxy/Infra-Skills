from __future__ import annotations

import gzip
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    REPO_ROOT
    / "skills"
    / "serving-timeline-profiling"
    / "scripts"
    / "summarize_torch_trace.py"
)


def synthetic_trace(rank: int) -> dict:
    events = []
    for step in range(4):
        base = step * 10_000
        external_id = step + 100
        events.extend(
            [
                {
                    "ph": "X",
                    "cat": "gpu_user_annotation",
                    "name": "forward_cudagraph",
                    "ts": base,
                    "dur": 8_000,
                    "args": {"External id": external_id},
                },
                {
                    "ph": "X",
                    "cat": "gpu_user_annotation",
                    "name": "forward_cudagraph",
                    "ts": base + 100,
                    "dur": 1_000,
                    "args": {"External id": external_id},
                },
                {
                    "ph": "X",
                    "cat": "cuda_runtime",
                    "name": "cudaGraphLaunch",
                    "ts": base + 50,
                    "dur": 20,
                    "args": {"correlation": external_id},
                },
                {
                    "ph": "X",
                    "cat": "kernel",
                    "name": "kernel_A",
                    "ts": base + 1_000,
                    "dur": 4_000,
                    "args": {"correlation": external_id, "device": rank},
                },
                {
                    "ph": "X",
                    "cat": "kernel",
                    "name": "kernel_B",
                    "ts": base + 6_000,
                    "dur": 2_000,
                    "args": {"correlation": external_id, "device": rank},
                },
            ]
        )
    return {
        "schemaVersion": 1,
        "distributedInfo": {"rank": rank, "world_size": 2},
        "traceEvents": events,
    }


class ServingTimelineProfileTest(unittest.TestCase):

    def test_plain_and_gzip_trace_summary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plain = root / "rank0.json"
            compressed_without_gz_suffix = root / "rank1.data"
            plain.write_text(json.dumps(synthetic_trace(0)), encoding="utf-8")
            with gzip.open(compressed_without_gz_suffix, "wt", encoding="utf-8") as handle:
                json.dump(synthetic_trace(1), handle)

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--step-regex",
                    "^forward_cudagraph$",
                    "--group",
                    "a=kernel_A",
                    str(plain),
                    str(compressed_without_gz_suffix),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual([row["rank"] for row in result["traces"]], [0, 1])

        for row in result["traces"]:
            self.assertEqual(row["matched_step_count"], 4)
            self.assertEqual(row["complete_cycle_count"], 2)
            self.assertEqual(row["forward_ms"]["median"], 8.0)
            self.assertEqual(row["cycle_ms"]["median"], 10.0)
            self.assertEqual(row["kernel_sum_ms_per_cycle"], 6.0)
            self.assertEqual(row["kernel_nodes_per_cycle"], 2.0)
            self.assertEqual(row["graph_launches_per_cycle"], 1.0)
            self.assertEqual(row["graph_child_kernel_nodes_per_cycle"], 2.0)
            self.assertEqual(row["gpu_busy_union_percent"], 60.0)
            self.assertEqual(row["max_all_stream_idle_gap_us"], 3_000.0)
            self.assertEqual(row["groups"]["a"]["ms_per_cycle"], 4.0)
            self.assertEqual(row["groups"]["other"]["ms_per_cycle"], 2.0)

        spread = result["cross_trace_spread"]
        self.assertEqual(spread["median_cycle_ms"]["spread_percent_of_mean"], 0.0)


if __name__ == "__main__":
    unittest.main()
