"""Bounded independent visual review and targeted scene repair before publication."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from .asset_refs import ASSET_LIBRARY_ROOT
from .contracts import ContractError
from .diagram_references import freeze_diagram
from .production import validate_storybook
from .schema_validation import validate_structure
from .storage import read_json, write_json, write_yaml


REVIEW_BATCH_SIZE = 20
IMMUTABLE_FIELDS = ("id", "order", "script_section_id", "voiceover", "timing")


def _diagram_provenance(graphic: dict) -> dict:
    """Adaptation describes the scene's treatment, not the diagram's provenance."""
    return {key: value for key, value in graphic.items() if key != "adaptation"}


def validate_findings(report: dict, scenes: list[dict], repo: Path) -> None:
    validate_structure(report, read_json(repo / "schemas/storybook-review.schema.json"))
    if [item["scene_id"] for item in report["scenes"]] != [scene["id"] for scene in scenes]:
        raise ContractError("Storybook review must evaluate every requested scene exactly once in order")
    if len(report["research"]["queries"]) > 3 or any(len(item["references"]) > 2 for item in report["scenes"]):
        raise ContractError("Storybook review exceeded its research budget")
    for item in report["scenes"]:
        for reference in item["references"]:
            if reference["use_mode"] != "reference" and not reference["license"].strip():
                raise ContractError("Diagram reuse requires recorded license or permission")


def review_storybook(*, writer, reviewer, storybook: dict, script: dict, direction_path: Path,
                     unit_dir: Path, repo: Path, scene_count: int | None = None) -> dict:
    """One review per batch; one repair and one recheck only for rejected scenes."""
    result = deepcopy(storybook)
    state = unit_dir / ".obscript"
    report_path = unit_dir / "storybook-review.yaml"
    ledger = {"schema_version": "1", "status": "reviewing", "batches": []}
    write_json(state / "storybook-review-draft.json", result)
    for offset in range(0, len(result["scenes"]), REVIEW_BATCH_SIZE):
        batch_number = offset // REVIEW_BATCH_SIZE + 1
        batch = result["scenes"][offset:offset + REVIEW_BATCH_SIZE]
        request_path = state / f"storybook-review-{batch_number:02d}.input.json"
        request = {
            "title": script["title"], "thesis": script["thesis"],
            "shared_direction": str(direction_path),
            "neighbors": [{"id": s["id"], "voiceover": s["voiceover"], "render_brief": s["render_brief"]}
                          for s in result["scenes"][max(0, offset - 1):offset + len(batch) + 1]
                          if s not in batch],
            # No repeated full script, source transcripts, or asset-search inventories.
            "scenes": [{key: scene[key] for key in
                        ("id", "script_section_id", "voiceover", "timing", "composition", "visual_elements", "onscreen_text",
                         "animation", "render_brief")} for scene in batch],
            "known_references": list({ref["source_url"]: ref for previous in ledger["batches"]
                                     for refs in previous["resolved_references"].values() for ref in refs}.values())[-6:],
        }
        write_json(request_path, request)
        findings, _ = reviewer.run(
            stage=f"review-storybook-{batch_number:02d}", skill="review-storybook", schema="storybook-review",
            web_search=True,
            prompt=f"Review every scene in {request_path}. Research is enabled for weak concepts, within the skill's budget. "
                   f"Use the visual-language map at {repo / 'skills/storybook/references/technical-visual-language.md'}. "
                   "Reuse known_references for repeated concepts before searching again. "
                   "Read shared standards only when needed to assess an apparent constraint. Keep each finding concise.",
        )
        validate_findings(findings, batch, repo)
        entry = {"initial": findings, "resolved_references": {}, "recheck": None}
        ledger["batches"].append(entry)
        write_yaml(report_path, ledger)
        rejected = [scene for scene, finding in zip(batch, findings["scenes"]) if finding["verdict"] == "revise"]
        if not rejected:
            continue
        rejected_ids = {scene["id"] for scene in rejected}
        downloads: dict[str, dict] = {}
        for finding in findings["scenes"]:
            if finding["scene_id"] not in rejected_ids:
                continue
            frozen = []
            for reference in finding["references"]:
                url = reference["figure_url"]
                if url and url not in downloads and len(downloads) < 6:
                    downloads[url] = freeze_diagram(reference, unit_dir / "diagram-references")
                downloaded = downloads.get(url)
                frozen.append({**reference, **{k: downloaded[k] for k in ("local_path", "sha256", "error")}}
                              if downloaded else {**reference, "local_path": "", "sha256": "", "error": "Not downloaded"})
            entry["resolved_references"][finding["scene_id"]] = frozen
        write_yaml(report_path, ledger)
        repair_path = state / f"storybook-repair-{batch_number:02d}.input.json"
        write_json(repair_path, {"scenes": rejected, "findings": [f for f in findings["scenes"]
                   if f["scene_id"] in rejected_ids], "references": entry["resolved_references"]})
        images = tuple(Path(item["local_path"]) for item in downloads.values() if item["local_path"])
        attachments = {"image_paths": images} if images else {}
        patch, _ = writer.run(
            stage=f"repair-storybook-{batch_number:02d}", skill="storybook", schema="storybook-revision",
            prompt=f"Repair only the rejected scenes in {repair_path}, using shared creative direction {direction_path}. "
                   "Return only those complete scene objects, in the same order. Keep id, order, script_section_id, "
                   "voiceover, and timing identical. Fix the specific explanatory defect; preserve other scenes and transitions. "
                   "Research results are supplied: do not search the web again. Use a downloaded diagram when it improves "
                   "the explanation, or adapt the source's graphical structure into an original scene. Record any downloaded "
                   "diagram used in external_graphics with its exact provenance, local_path, hash and use_mode "
                   "(omit only the download error field). You may rewrite adaptation to describe the repaired scene's "
                   "actual treatment. Reference-only diagrams must not be displayed. "
                   "For reuse/animate, select its local_path as a foreground asset in all production fields; a frozen diagram "
                   "can satisfy foreground coverage. Preserve required raster-background coverage. Do not invent downloaded paths.",
            **attachments,
        )
        if set(patch) != {"scenes"} or [s["id"] for s in patch["scenes"]] != [s["id"] for s in rejected]:
            raise ContractError("Storybook repair must return only the rejected scenes in order")
        for old, new in zip(rejected, patch["scenes"]):
            if any(new.get(key) != old[key] for key in IMMUTABLE_FIELDS):
                raise ContractError(f"{old['id']}: visual repair changed narration, identity, or timing")
            allowed = [{k: v for k, v in ref.items() if k != "error"} for ref in
                       entry["resolved_references"][old["id"]] if ref["local_path"]]
            allowed_provenance = [_diagram_provenance(ref) for ref in allowed + old.get("external_graphics", [])]
            for graphic in new.get("external_graphics", []):
                if _diagram_provenance(graphic) not in allowed_provenance:
                    raise ContractError(f"{old['id']}: repair invented or altered diagram provenance")
            original_paths = {asset["path"] for asset in old["design_pillars"]["assets"]["selected_assets"]}
            diagram_paths = {g["local_path"] for g in new.get("external_graphics", []) if g["use_mode"] != "reference"}
            for asset in new["design_pillars"]["assets"]["selected_assets"]:
                path = Path(asset["path"])
                if (asset["path"] not in original_paths and asset["path"] not in diagram_paths
                        and not (path.is_absolute() and path.resolve().is_relative_to(ASSET_LIBRARY_ROOT.resolve()))):
                    raise ContractError(f"{old['id']}: new external asset has no verified diagram provenance")
            result["scenes"][new["order"] - 1] = new
        validate_storybook(script, result, storybook["target_duration_seconds"], scene_count=scene_count)
        write_json(state / "storybook-review-draft.json", result)
        recheck_path = state / f"storybook-recheck-{batch_number:02d}.input.json"
        write_json(recheck_path, {"scenes": patch["scenes"], "original_findings": entry["initial"]})
        recheck, _ = reviewer.run(
            stage=f"recheck-storybook-{batch_number:02d}", skill="review-storybook", schema="storybook-review",
            prompt=f"Check only the repaired scenes at {recheck_path}. Research is disabled; use saved findings and references. "
                   "Does each actual visible action now explain the concept? Do not revisit passing scenes or add style preferences.",
            **attachments,
        )
        validate_findings(recheck, patch["scenes"], repo)
        entry["recheck"] = recheck
        remaining = [f["scene_id"] for f in recheck["scenes"] if f["verdict"] == "revise"]
        if remaining:
            ledger["status"] = "needs_revision"
            write_yaml(report_path, ledger)
            raise ContractError(f"Storybook visual review still requests revision: {', '.join(remaining)}; inspect {report_path}")
        write_yaml(report_path, ledger)
    ledger["status"] = "pass"
    write_yaml(report_path, ledger)
    write_json(state / "storybook-review.json", ledger)
    return result
