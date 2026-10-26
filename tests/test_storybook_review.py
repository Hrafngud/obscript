from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from obscript.contracts import ContractError
from obscript.diagram_references import MAX_IMAGE_BYTES, freeze_diagram
from obscript.production import invalidate_downstream, validate_storybook
from obscript.storage import file_sha256, read_json, read_yaml, render_storybook
from obscript.storybook_edits import apply_readable_storybook
from obscript.storybook_review import review_storybook
from test_visual_production import REPO, FOREGROUND_ASSET, script_fixture, story_fixture, visual_review_fixture


def reference_fixture():
    return {"title": "Request diagram", "source_url": "https://example.org/article",
            "figure_url": "https://example.org/figure.png", "license": "CC BY 4.0",
            "attribution": "Example Author", "use_mode": "animate",
            "adaptation": "Trace the request through the original routes and highlight the changed output."}


class StorybookReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.story = story_fixture()
        self.writer = Mock()
        self.reviewer = Mock()
        self.findings = visual_review_fixture(self.story["scenes"])
        self.reviewer.run.return_value = self.findings, self.root / "findings.json"

    def review(self):
        return review_storybook(writer=self.writer, reviewer=self.reviewer, storybook=self.story,
                                script=script_fixture(), direction_path=self.root / "direction.md",
                                unit_dir=self.root, repo=REPO)

    def reject_first(self, *, remains_rejected=False, reference=None):
        self.findings = visual_review_fixture(self.story["scenes"], ["scene-001"])
        if reference:
            self.findings["scenes"][0]["references"] = [reference]
        final = visual_review_fixture(self.story["scenes"][:1], ["scene-001"] if remains_rejected else [])
        self.reviewer.run.side_effect = [(self.findings, self.root / "initial.json"), (final, self.root / "final.json")]
        repaired = copy.deepcopy(self.story["scenes"][0])
        repaired["render_brief"] += " Trace the cause and compare the state before and after crossing it."
        self.writer.run.return_value = {"scenes": [repaired]}, self.root / "repair.json"
        return repaired

    def test_passing_batch_needs_one_review_and_no_rewrite(self):
        self.assertEqual(self.review(), self.story)
        self.writer.run.assert_not_called()
        self.reviewer.run.assert_called_once()
        self.assertTrue(self.reviewer.run.call_args.kwargs["web_search"])
        self.assertEqual(read_yaml(self.root / "storybook-review.yaml")["status"], "pass")
        request = read_json(self.root / ".obscript/storybook-review-01.input.json")
        self.assertNotIn("design_pillars", request["scenes"][0])

    def test_only_flagged_scene_is_repaired_and_rechecked_without_research(self):
        repaired = self.reject_first()
        result = self.review()
        self.assertEqual(result["scenes"][0], repaired)
        self.assertEqual(result["scenes"][1:], self.story["scenes"][1:])
        self.assertEqual(self.story, story_fixture())
        self.writer.run.assert_called_once()
        self.assertEqual(self.writer.run.call_args.kwargs["schema"], "storybook-revision")
        self.assertNotIn("web_search", self.reviewer.run.call_args.kwargs)
        request = read_json(self.root / ".obscript/storybook-repair-01.input.json")
        self.assertEqual([s["id"] for s in request["scenes"]], ["scene-001"])

    def test_repair_cannot_change_narration_or_timing_or_other_scenes(self):
        for field in ("voiceover", "timing", "id"):
            with self.subTest(field=field):
                repaired = self.reject_first()
                repaired[field] = self.story["scenes"][1][field]
                with self.assertRaises(ContractError):
                    self.review()

    def test_unresolved_scene_stops_after_one_repair_with_inspectable_draft(self):
        repaired = self.reject_first(remains_rejected=True)
        with self.assertRaisesRegex(ContractError, "still requests revision: scene-001"):
            self.review()
        self.assertEqual(self.reviewer.run.call_count, 2)
        self.writer.run.assert_called_once()
        self.assertEqual(read_yaml(self.root / "storybook-review.yaml")["status"], "needs_revision")
        self.assertEqual(read_json(self.root / ".obscript/storybook-review-draft.json")["scenes"][0], repaired)

    def test_every_scene_requires_a_finding_in_order(self):
        self.findings["scenes"].pop()
        with self.assertRaisesRegex(ContractError, "every requested scene"):
            self.review()
        self.writer.run.assert_not_called()

    def test_final_partial_review_batch_is_processed(self):
        def run(**kwargs):
            number = kwargs["stage"].rsplit("-", 1)[1]
            request = read_json(self.root / f".obscript/storybook-review-{number}.input.json")
            return visual_review_fixture(request["scenes"]), self.root / "finding.json"
        self.reviewer.run.side_effect = run
        with patch("obscript.storybook_review.REVIEW_BATCH_SIZE", 3):
            self.review()
        self.assertEqual(self.reviewer.run.call_count, 2)
        request = read_json(self.root / ".obscript/storybook-review-02.input.json")
        self.assertEqual([s["id"] for s in request["scenes"]], ["scene-004"])
        self.assertEqual(request["neighbors"][0]["id"], "scene-003")

    def test_downloaded_diagram_is_attached_and_can_replace_a_library_foreground(self):
        reference = reference_fixture()
        repaired = self.reject_first(reference=reference)
        image = self.root / "figure.png"
        image.write_bytes(b"image fixture")
        graphic = {**reference, "local_path": str(image), "sha256": file_sha256(image)}
        repaired["external_graphics"] = [graphic]
        old_path = FOREGROUND_ASSET
        path = str(image)
        plan = repaired["design_pillars"]["assets"]
        plan["selected_assets"][0]["path"] = path
        plan["candidates_considered"].append(path)
        repaired["visual_elements"][0]["content"] = path
        repaired["asset_requirements"][0]["description"] = path
        repaired["render_brief"] = repaired["render_brief"].replace(old_path, path)
        with patch("obscript.storybook_review.freeze_diagram", return_value={**graphic, "error": ""}):
            result = self.review()
        self.assertEqual(self.writer.run.call_args.kwargs["image_paths"], (image,))
        self.assertEqual(self.reviewer.run.call_args.kwargs["image_paths"], (image,))
        validate_storybook(script_fixture(), result, 12)
        baseline = render_storybook(result, script_fixture())
        edited, _, _ = apply_readable_storybook(result, baseline.replace("Trace the cause", "Follow the cause"), baseline)
        validate_storybook(script_fixture(), edited, 12)
        image.write_bytes(b"changed")
        with self.assertRaisesRegex(ContractError, "missing or changed"):
            validate_storybook(script_fixture(), result, 12)

    def test_reference_only_diagram_cannot_be_displayed(self):
        reference = reference_fixture()
        reference["use_mode"] = "reference"
        repaired = self.reject_first(reference=reference)
        graphic = {**reference, "local_path": FOREGROUND_ASSET, "sha256": file_sha256(Path(FOREGROUND_ASSET))}
        repaired["external_graphics"] = [graphic]
        with patch("obscript.storybook_review.freeze_diagram", return_value={**graphic, "error": ""}):
            with self.assertRaisesRegex(ContractError, "reference-only diagram"):
                self.review()

    def test_repair_can_rewrite_adaptation_for_supplied_or_existing_diagram(self):
        image = self.root / "figure.png"
        image.write_bytes(b"image fixture")
        reference = {**reference_fixture(), "use_mode": "reference"}
        graphic = {**reference, "local_path": str(image), "sha256": file_sha256(image)}
        for existing in (False, True):
            with self.subTest(existing=existing):
                self.story["scenes"][0]["external_graphics"] = [graphic] if existing else []
                repaired = self.reject_first(reference=None if existing else reference)
                repaired["external_graphics"] = [{**graphic, "adaptation": "Compare two independent optimizer lanes."}]
                with patch("obscript.storybook_review.freeze_diagram", return_value={**graphic, "error": ""}):
                    result = self.review()
                self.assertEqual(result["scenes"][0]["external_graphics"], repaired["external_graphics"])

    def test_repair_cannot_change_diagram_identity_or_permissions(self):
        image = self.root / "figure.png"
        image.write_bytes(b"image fixture")
        reference = {**reference_fixture(), "use_mode": "reference"}
        graphic = {**reference, "local_path": str(image), "sha256": file_sha256(image)}
        changes = {"title": "Different source", "source_url": "https://example.org/other",
                   "figure_url": "https://example.org/other.png", "license": "CC0",
                   "attribution": "Another author", "use_mode": "reuse",
                   "local_path": str(self.root / "other.png"), "sha256": "0" * 64}
        for existing in (False, True):
            for field, value in changes.items():
                with self.subTest(existing=existing, field=field):
                    self.story["scenes"][0]["external_graphics"] = [graphic] if existing else []
                    repaired = self.reject_first(reference=None if existing else reference)
                    repaired["external_graphics"] = [{**graphic, field: value,
                                                     "adaptation": "Compare two independent optimizer lanes."}]
                    with patch("obscript.storybook_review.freeze_diagram", return_value={**graphic, "error": ""}):
                        with self.assertRaisesRegex(ContractError, "invented or altered diagram provenance"):
                            self.review()

    def test_new_external_asset_requires_recorded_provenance(self):
        repaired = self.reject_first()
        repaired["design_pillars"]["assets"]["selected_assets"].append({
            "path": str(self.root / "unrecorded.png"), "usage": "foreground", "semantic_role": "Diagram"})
        with self.assertRaisesRegex(ContractError, "no verified diagram provenance"):
            self.review()

    def test_production_invalidation_retains_review_but_replanning_archives_it(self):
        self.review()
        invalidate_downstream(self.root, "storybook")
        self.assertTrue((self.root / "storybook-review.yaml").exists())
        invalidate_downstream(self.root, "storybook", replan=True)
        self.assertFalse((self.root / "storybook-review.yaml").exists())


class DiagramDownloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.reference = reference_fixture()

    def response(self, data):
        response = Mock()
        response.geturl.return_value = self.reference["figure_url"]
        response.read.return_value = data
        opener = Mock()
        opener.open.return_value.__enter__ = Mock(return_value=response)
        opener.open.return_value.__exit__ = Mock(return_value=False)
        return opener

    def test_download_is_frozen_and_reused_with_provenance(self):
        opener = self.response(b"\x89PNG\r\n\x1a\nimage bytes")
        with patch("obscript.diagram_references.public_url"), patch("obscript.diagram_references.build_opener", return_value=opener):
            first = freeze_diagram(self.reference, self.root)
            second = freeze_diagram(self.reference, self.root)
        self.assertEqual(first, second)
        self.assertEqual(first["attribution"], "Example Author")
        self.assertEqual(first["sha256"], file_sha256(Path(first["local_path"])))
        opener.open.assert_called_once()

    def test_html_oversize_and_network_errors_preserve_optional_reference(self):
        for data in (b"<html>not an image</html>", b"x" * (MAX_IMAGE_BYTES + 1)):
            with self.subTest(size=len(data)), patch("obscript.diagram_references.public_url"), \
                 patch("obscript.diagram_references.build_opener", return_value=self.response(data)):
                result = freeze_diagram(self.reference, self.root)
                self.assertFalse(result["local_path"])
                self.assertTrue(result["error"])
                self.assertEqual(result["source_url"], self.reference["source_url"])
        with patch("obscript.diagram_references.public_url", side_effect=OSError("offline")):
            self.assertEqual(freeze_diagram(self.reference, self.root)["error"], "offline")

    def test_private_addresses_are_rejected_before_fetching(self):
        with patch("obscript.diagram_references.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("127.0.0.1", 443))]), \
             patch("obscript.diagram_references.build_opener") as opener:
            result = freeze_diagram(self.reference, self.root)
        self.assertIn("public addresses", result["error"])
        opener.assert_not_called()
