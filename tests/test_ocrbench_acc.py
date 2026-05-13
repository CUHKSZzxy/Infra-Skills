import base64
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "e2e-accuracy-benchmark"
    / "scripts"
    / "ocrbench_acc.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("ocrbench_acc", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class OCRBenchAccTest(unittest.TestCase):

    def test_scores_use_vlmevalkit_substring_rules(self):
        mod = load_module()
        image = base64.b64encode(b"\xff\xd8\xff\xd9").decode()
        records = [
            mod.OCRBenchRecord(
                0,
                image,
                "what is written?",
                ["CENTRE"],
                "Regular Text Recognition",
            ),
            mod.OCRBenchRecord(
                1,
                image,
                "what number?",
                ["12 34"],
                "Handwritten Mathematical Expression Recognition",
            ),
            mod.OCRBenchRecord(2, image, "which word?", ["FRIEND"], "Irregular Text Recognition"),
        ]
        responses = iter(["The word is centre.", "12\n34", "enemy"])

        result = mod.run_eval(records, lambda _record: next(responses), num_threads=1)

        self.assertEqual(result.correct, 2)
        self.assertEqual(result.total, 3)
        self.assertEqual(result.accuracy, 2 / 3)
        self.assertEqual(result.request_errors, 0)
        self.assertEqual(result.scores["Text Recognition"], 1)
        self.assertEqual(result.scores["Handwritten Mathematical Expression Recognition"], 1)
        self.assertEqual(result.items[2].score, 0.0)

    def test_run_eval_counts_request_errors(self):
        mod = load_module()
        image = base64.b64encode(b"\xff\xd8\xff\xd9").decode()
        records = [
            mod.OCRBenchRecord(0, image, "what is written?", ["CENTRE"], "Regular Text Recognition")
        ]

        def failing_sampler(_record):
            raise RuntimeError("server unavailable")

        result = mod.run_eval(records, failing_sampler, num_threads=1)

        self.assertEqual(result.correct, 0)
        self.assertEqual(result.total, 1)
        self.assertEqual(result.request_errors, 1)
        self.assertIn("RuntimeError", result.items[0].error)

    def test_build_messages_uses_openai_image_url_data_uri(self):
        mod = load_module()
        image = base64.b64encode(b"\xff\xd8\xff\xd9").decode()
        record = mod.OCRBenchRecord(
            7, image, "Read the label.", ["ABC"], "Regular Text Recognition"
        )

        messages = mod.build_messages(record)

        content = messages[0]["content"]
        self.assertEqual(content[0]["type"], "image_url")
        self.assertTrue(content[0]["image_url"]["url"].startswith("data:image/jpeg;base64,"))
        self.assertEqual(content[1]["type"], "text")
        self.assertIn("Answer the question using a single word or phrase.", content[1]["text"])

    def test_build_messages_handles_long_jpeg_base64_starting_with_slash(self):
        mod = load_module()
        image = base64.b64encode(b"\xff\xd8\xff" + (b"x" * 5000)).decode()
        self.assertTrue(image.startswith("/9j"))
        record = mod.OCRBenchRecord(
            8, image, "Read the label.", ["ABC"], "Regular Text Recognition"
        )

        messages = mod.build_messages(record)

        url = messages[0]["content"][0]["image_url"]["url"]
        self.assertTrue(url.startswith("data:image/jpeg;base64,/9j"))

    def test_read_tsv_accepts_ocrbench_answer_lists(self):
        mod = load_module()
        image = base64.b64encode(b"\x89PNG\r\n\x1a\n").decode()
        with tempfile.TemporaryDirectory() as tmp:
            data_path = Path(tmp) / "ocrbench.tsv"
            data_path.write_text(
                "index\timage\tquestion\tanswer\tcategory\n"
                f"0\t{image}\twhat is shown?\t['HELLO', 'HI']\tScene Text-centric VQA\n",
                encoding="utf-8",
            )

            records = mod.read_tsv(str(data_path))

        self.assertEqual(
            records,
            [
                mod.OCRBenchRecord(
                    index=0,
                    image=image,
                    question="what is shown?",
                    answers=["HELLO", "HI"],
                    category="Scene Text-centric VQA",
                )
            ],
        )


if __name__ == "__main__":
    unittest.main()
