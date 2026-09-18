from __future__ import annotations

import unittest

from obscript.contracts import (
    ContractError,
    choose_target_duration,
    parse_command_tokens,
    parse_duration,
    script_duration_bounds,
)


class DurationTests(unittest.TestCase):
    def test_duration_forms(self) -> None:
        self.assertEqual(parse_duration("480"), 480)
        self.assertEqual(parse_duration("8m"), 480)
        self.assertEqual(parse_duration("1.5h"), 5400)
        self.assertEqual(parse_duration("08:30"), 510)
        self.assertEqual(parse_duration("1:02:03"), 3723)

    def test_invalid_duration(self) -> None:
        with self.assertRaises(ContractError):
            parse_duration("8 minutes")

    def test_script_review_duration_tolerance(self) -> None:
        for target, bounds in [(100, (70, 130)), (126, (89, 163)), (1, (1, 1))]:
            with self.subTest(target=target):
                self.assertEqual(script_duration_bounds(target), bounds)
                minimum, maximum = bounds
                self.assertGreaterEqual(minimum * 100, target * 70)
                self.assertLess((minimum - 1) * 100, target * 70)
                self.assertLessEqual(maximum * 100, target * 130)
                self.assertGreater((maximum + 1) * 100, target * 130)

    def test_reported_run_is_within_duration_tolerance(self) -> None:
        minimum, maximum = script_duration_bounds(126)
        self.assertLessEqual(minimum, 151)
        self.assertGreaterEqual(maximum, 151)

    def test_script_review_rejects_invalid_target(self) -> None:
        for target in [0, -1]:
            with self.subTest(target=target), self.assertRaises(ContractError):
                script_duration_bounds(target)


class GrammarTests(unittest.TestCase):
    def test_base(self) -> None:
        spec = parse_command_tokens(["video"])
        self.assertEqual((spec.pipeline, spec.time_controller, spec.format), ("single", "normal", "source"))

    def test_full_composition(self) -> None:
        spec = parse_command_tokens(["remix", "compress", "essay", "a,b,c"])
        self.assertEqual(spec.sources, ("a", "b", "c"))

    def test_split_options(self) -> None:
        spec = parse_command_tokens(
            ["split", "extend", "topics", "video"],
            target_duration="8m",
            split_count=4,
        )
        self.assertEqual(spec.target_duration_seconds, 480)
        self.assertEqual(spec.split_count, 4)

    def test_rejects_wrong_modifier_order(self) -> None:
        with self.assertRaisesRegex(ContractError, "ordered"):
            parse_command_tokens(["essay", "compress", "video"])

    def test_remix_cardinality(self) -> None:
        with self.assertRaisesRegex(ContractError, "two or more"):
            parse_command_tokens(["remix", "video"])

    def test_non_remix_cardinality(self) -> None:
        with self.assertRaisesRegex(ContractError, "exactly one"):
            parse_command_tokens(["topics", "a,b"])

    def test_target_requires_controller(self) -> None:
        with self.assertRaisesRegex(ContractError, "requires"):
            parse_command_tokens(["video"], target_duration="8m")


class TargetTests(unittest.TestCase):
    def test_automatic_targets(self) -> None:
        knowledge = {"recommended_duration_seconds": 1000, "sources": []}
        self.assertEqual(choose_target_duration(knowledge, "normal", None), 1000)
        self.assertEqual(choose_target_duration(knowledge, "compress", None), 600)
        self.assertEqual(choose_target_duration(knowledge, "extend", None), 1500)
        self.assertEqual(choose_target_duration(knowledge, "compress", 300), 300)


if __name__ == "__main__":
    unittest.main()
