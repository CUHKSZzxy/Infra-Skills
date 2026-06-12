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
    / "mmlu_pro_acc.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("mmlu_pro_acc", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class MMLUProAccTest(unittest.TestCase):

    def test_extract_answer_prefers_answer_marker(self):
        mod = load_module()

        self.assertEqual(
            mod.extract_answer("I considered A.\nANSWER: C", list("ABCD")),
            "C",
        )
        self.assertEqual(mod.extract_answer("The answer is (B).", list("ABCD")), "B")
        self.assertEqual(mod.extract_answer("Reasoning complete.\nD", list("ABCD")), "D")
        self.assertIsNone(mod.extract_answer("I do not know.", list("ABCDEFGHIJ")))
        self.assertIsNone(mod.extract_answer("ANSWER: J", list("ABCD")))

    def test_extract_answer_skips_option_word_before_final_marker(self):
        mod = load_module()

        response = (
            "Therefore, the purchaser (Option I) has standing.\n\n"
            "Answer: Option I.\n\n"
            "ANSWER: I"
        )

        self.assertEqual(mod.extract_answer(response, list("ABCDEFGHIJ")), "I")

    def test_run_eval_scores_exact_letters_and_counts_extraction_errors(self):
        mod = load_module()
        records = [
            mod.MMLUProRecord(0, "q0", ["a", "b", "c", "d"], "C", "math"),
            mod.MMLUProRecord(1, "q1", ["a", "b", "c", "d"], "B", "history"),
            mod.MMLUProRecord(2, "q2", ["a", "b", "c", "d"], "A", "math"),
        ]
        responses = iter(["Reasoning\nANSWER: C", "ANSWER: D", "no final answer"])

        result = mod.run_eval(
            records,
            lambda _prompt: next(responses),
            num_threads=1,
            progress_interval=0,
        )

        self.assertEqual(result.correct, 1)
        self.assertEqual(result.total, 3)
        self.assertEqual(result.accuracy, 1 / 3)
        self.assertEqual(result.request_errors, 0)
        self.assertEqual(result.extraction_errors, 1)
        self.assertEqual(result.category_scores["math"], 0.5)
        self.assertEqual(result.category_totals["math"], 2)

    def test_run_eval_counts_request_errors(self):
        mod = load_module()
        records = [
            mod.MMLUProRecord(0, "q0", ["a", "b", "c", "d"], "A", "math")
        ]

        def failing_sampler(_prompt):
            raise RuntimeError("server unavailable")

        result = mod.run_eval(
            records,
            failing_sampler,
            num_threads=1,
            progress_interval=0,
        )

        self.assertEqual(result.correct, 0)
        self.assertEqual(result.request_errors, 1)
        self.assertIn("RuntimeError", result.items[0].error)

    def test_record_from_mapping_accepts_string_options_and_answer_index(self):
        mod = load_module()
        record = mod.record_from_mapping(
            {
                "question": "pick one",
                "options": "A. alpha\nB. beta\nC. gamma",
                "answer_index": 1,
                "category": "other",
            },
            7,
        )

        self.assertEqual(record.options, ["alpha", "beta", "gamma"])
        self.assertEqual(record.answer, "B")
        self.assertEqual(record.category, "other")

    def test_read_jsonl_local_data(self):
        mod = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            data_path = Path(tmp) / "mmlu_pro.jsonl"
            data_path.write_text(
                '{"question":"q","options":["a","b"],"answer":"B","category":"math"}\n',
                encoding="utf-8",
            )
            records = [
                mod.record_from_mapping(row, idx)
                for idx, row in enumerate(mod.read_jsonl(data_path))
            ]

        self.assertEqual(
            records, [mod.MMLUProRecord(0, "q", ["a", "b"], "B", "math")]
        )


if __name__ == "__main__":
    unittest.main()
