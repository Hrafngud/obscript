from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

from .codex_agent import CodexAgent
from .contracts import ContractError, choose_target_duration
from .models import CommandSpec, RuntimeConfig
from .projects import create_project, find_project, update_project
from .production import ProductionAgent, invalidate_downstream, validate_storybook
from .post_production import PostProductionAgent
from .storage import (
    copy_if_present,
    file_sha256,
    read_json,
    read_yaml,
    read_creative_direction,
    creative_direction_reference,
    render_plan,
    render_script,
    render_storybook,
    slugify,
    unique_directory,
    write_json,
    write_yaml,
)
from .transcribe import ingest_source


@dataclass(frozen=True)
class PipelineResult:
    project_root: Path
    outputs: tuple[Path, ...]
    passed_review: bool


@dataclass(frozen=True)
class ApprovedScript:
    script: dict
    script_path: Path
    knowledge_path: Path
    plan_path: Path
    review_path: Path
    target_seconds: int


class Pipeline:
    def __init__(self, config: RuntimeConfig) -> None:
        self.config = config

    def run(self, spec: CommandSpec) -> PipelineResult:
        if spec.post_production and not spec.project_id:
            raise ContractError("Post-production requires an existing project ID")
        if spec.project_id:
            project_root = find_project(self.config.output_dir, spec.project_id)
            if project_root is None:
                raise ContractError(f"Project not found: {spec.project_id}")
        else:
            name = self.config.project_name or Path(spec.sources[0]).stem
            project_root = unique_directory(
                self.config.output_dir,
                slugify(name, datetime.now().strftime("video-%Y%m%d-%H%M%S")),
            )
            create_project(project_root, spec, self.config.creative_direction_path)
        print(f"[obscript] project ID: {read_json(project_root / 'project.json')['id']}", flush=True)
        print(f"[obscript] projeto: {project_root}", flush=True)
        update_project(project_root)
        try:
            result = self._run(spec, project_root)
        except Exception as exc:
            update_project(project_root, status="failed", error=str(exc))
            raise
        phase = "post-production" if spec.post_production else "render" if spec.render else "storybook" if spec.storybook else "script"
        update_project(project_root, phase=phase if result.passed_review else None,
                       status="complete" if result.passed_review else "needs_review",
                       creative_direction=self.config.creative_direction_path)
        return result

    def _run(self, spec: CommandSpec, project_root: Path) -> PipelineResult:
        if spec.post_production:
            return self._run_post_production(project_root)
        direction_path = self.config.creative_direction_path
        direction = read_creative_direction(direction_path) if spec.storybook or spec.render else None
        sources = self._import_sources(spec, project_root)
        if spec.pipeline == "remix" and len(sources) < 2:
            raise ContractError("remix requires at least two videos after source expansion")
        if spec.pipeline == "split" and len(sources) != 1:
            raise ContractError("split requires one video, but the source expanded to a playlist")
        agent = CodexAgent(
            executable=self.config.codex,
            repo_root=self.config.repo_root,
            project_root=project_root,
            model=self.config.model,
            reasoning_effort=self.config.reasoning_effort,
            verbose=self.config.verbose,
        )
        write_yaml(
            project_root / "run.yaml",
            {
                "project_id": read_json(project_root / "project.json")["id"],
                "created_at": read_json(project_root / "project.json")["created_at"],
                "pipeline": spec.pipeline,
                "time_controller": spec.time_controller,
                "format": spec.format,
                "target_duration_seconds": spec.target_duration_seconds,
                "split_count": spec.split_count,
                "render": spec.render,
                "storybook": spec.storybook,
                "creative_direction": creative_direction_reference(direction_path, direction) if direction else None,
                "sources": list(spec.sources),
                "agent": "Codex CLI",
                "model": self.config.model or "configured default",
                "reasoning_effort": self.config.reasoning_effort,
            },
        )

        analyses: list[dict] = []
        for index, relative_dir in enumerate(sources, 1):
            source_dir = project_root / relative_dir
            transcript_txt = source_dir / "transcript.txt"
            analysis_path = source_dir / "analysis.json"
            if analysis_path.exists():
                analysis = read_json(analysis_path)
            else:
                analysis, _ = agent.run(
                    stage=f"analyze-source-{index:02d}",
                    skill="analyze-source",
                    schema="knowledge",
                    prompt=f"""Analyze the transcript at {transcript_txt}.
Source metadata is at {source_dir / 'source.json'}.
Create a canonical PT-BR knowledge model. Set kind to single and narrative.format to source.
Use stable topic IDs prefixed with source-{index:02d}/. Preserve factual qualifications and do not write narration.""",
                )
                write_json(analysis_path, analysis)
            analyses.append(analysis)
            write_yaml(source_dir / "analysis.yaml", analysis)
            print(f"[obscript] análise: {analysis_path}", flush=True)

        if spec.pipeline == "remix":
            analyses_path = project_root / ".obscript" / "source-analyses.json"
            write_json(analyses_path, analyses)
            remix_path = project_root / ".obscript/remix-knowledge.json"
            if remix_path.exists():
                knowledge = read_json(remix_path)
            else:
                knowledge, _ = agent.run(
                    stage="remix",
                    skill="remix",
                    schema="knowledge",
                    prompt=f"""Merge every knowledge model in {analyses_path} into one genuinely unified model.
Set kind to remix. Deduplicate overlap, preserve provenance in source_refs, surface unresolved contradictions, and create a new defensible thesis.""",
                )
                write_json(remix_path, knowledge)
        else:
            knowledge = analyses[0]

        if spec.pipeline == "split":
            knowledge_path = project_root / ".obscript" / "pre-split-knowledge.json"
            write_json(knowledge_path, knowledge)
            count_instruction = (
                f"Produce exactly {spec.split_count} parts when conceptually viable."
                if spec.split_count
                else "Choose the number of parts justified by natural conceptual boundaries."
            )
            target_instruction = (
                f"Aim for about {spec.target_duration_seconds} seconds per part."
                if spec.target_duration_seconds
                else "Recommend a defensible duration for every part."
            )
            split_path = project_root / ".obscript/split-result.json"
            if split_path.exists():
                split_result = read_json(split_path)
            else:
                split_result, _ = agent.run(
                    stage="split",
                    skill="split",
                    schema="split",
                    prompt=f"""Split the knowledge model at {knowledge_path} semantically, never by equal transcript intervals.
{count_instruction}
{target_instruction}
Each part must be a complete knowledge model with kind split and narrative.format source.""",
                )
                write_json(split_path, split_result)
            write_yaml(
                project_root / "split-plan.yaml",
                {
                    "rationale": split_result["rationale"],
                    "parts": [
                        {
                            "index": index,
                            "thesis": part["summary"]["thesis"],
                            "recommended_duration_seconds": part["recommended_duration_seconds"],
                        }
                        for index, part in enumerate(split_result["parts"], 1)
                    ],
                },
            )
            units = [
                (project_root / f"video-{index:02d}", part)
                for index, part in enumerate(split_result["parts"], 1)
            ]
        elif spec.pipeline == "single" and len(analyses) > 1:
            write_yaml(
                project_root / "playlist-plan.yaml",
                {
                    "mode": "independent",
                    "videos": [
                        {
                            "index": index,
                            "title": part["sources"][0]["title"],
                            "thesis": part["summary"]["thesis"],
                        }
                        for index, part in enumerate(analyses, 1)
                    ],
                },
            )
            units = [
                (project_root / f"video-{index:02d}", part)
                for index, part in enumerate(analyses, 1)
            ]
        else:
            units = [(project_root, knowledge)]

        known_units = read_json(project_root / "project.json")["units"]
        for unit_dir, _ in units:
            if unit_dir.relative_to(project_root).as_posix() not in known_units:
                update_project(project_root, phase="transcript", unit=unit_dir)
        outputs: list[Path] = []
        all_passed = True
        for unit_dir, unit_knowledge in units:
            unit_dir.mkdir(parents=True, exist_ok=True)
            unit_agent = agent if unit_dir == project_root else CodexAgent(
                executable=self.config.codex, repo_root=self.config.repo_root,
                project_root=unit_dir, model=self.config.model,
                reasoning_effort=self.config.reasoning_effort, verbose=self.config.verbose,
            )
            approved = self._produce_script(unit_agent, spec, unit_dir, unit_knowledge)
            outputs.append(unit_dir / "script.md")
            all_passed = all_passed and approved is not None
            if approved is not None:
                update_project(project_root, phase="script", unit=unit_dir)
                if not (spec.storybook or spec.render):
                    continue
                if read_creative_direction(direction_path) != direction:
                    raise ContractError("Shared creative direction changed during this run; rerun to rebuild the scene plans")
                storybook, storybook_path = self._get_storybook(unit_agent, unit_dir, approved, direction_path, render=spec.render)
                update_project(project_root, phase="storybook", unit=unit_dir)
                outputs.extend([unit_dir / "storybook.md", unit_dir / "storybook.yaml"])
                if spec.render:
                    outputs.append(self._produce_video(unit_dir, approved, direction_path, storybook_path))
                    outputs.append(unit_dir / "production.yaml")
                    update_project(project_root, phase="render", unit=unit_dir)
        return PipelineResult(project_root, tuple(outputs), all_passed)

    def _run_post_production(self, project_root: Path) -> PipelineResult:
        metadata = read_json(project_root / "project.json")
        units = metadata.get("units", {})
        if not units or any(phase not in {"render", "post-production"} for phase in units.values()):
            raise ContractError("Post-production requires a completed render for every video; run PROJECT_ID --render first")
        unit_dirs = []
        for name in units:
            unit_dir = (project_root / name).resolve()
            if not unit_dir.is_relative_to(project_root.resolve()):
                raise ContractError("Invalid production unit path")
            unit_dirs.append(unit_dir)
        # Validate every unit before invoking a side-effecting executor.
        agents = [PostProductionAgent(self.config, unit_dir) for unit_dir in unit_dirs]
        for agent in agents:
            agent.validate_inputs()
        outputs = []
        for unit_dir, agent in zip(unit_dirs, agents):
            outputs.append(agent.polish())
            outputs.extend([unit_dir / "post-production.yaml", unit_dir / "post-production/report.md"])
            update_project(project_root, phase="post-production", unit=unit_dir)
        return PipelineResult(project_root, tuple(outputs), True)

    def _import_sources(self, spec: CommandSpec, project_root: Path) -> list[str]:
        checkpoint = project_root / ".obscript/imports.json"
        imports = read_json(checkpoint) if checkpoint.exists() else []
        for source in spec.sources[len(imports):]:
            print(f"[obscript] preparando fonte: {source}", flush=True)
            assets = ingest_source(source, ytstt=self.config.ytstt,
                                   transcripts_dir=self.config.transcripts_dir,
                                   cookies_from_browser=self.config.cookies_from_browser,
                                   cookies=self.config.cookies)
            directories = []
            count = sum(len(item) for item in imports)
            for index, asset in enumerate(assets, count + 1):
                source_dir = project_root / "sources" / f"source-{index:02d}-{slugify(asset.title)}"
                source_dir.mkdir(parents=True, exist_ok=True)
                txt = copy_if_present(asset.transcript_txt, source_dir / "transcript.txt")
                srt = copy_if_present(asset.transcript_srt, source_dir / "transcript.srt")
                data = copy_if_present(asset.transcript_json, source_dir / "transcript.json")
                write_json(source_dir / "source.json", {
                    "id": f"source-{index:02d}", "title": asset.title, "source": asset.original,
                    "language": asset.language, "duration_seconds": round(asset.duration_seconds, 3),
                    "transcript_txt": str(txt), "transcript_srt": str(srt) if srt else None,
                    "transcript_json": str(data) if data else None,
                })
                directories.append(source_dir.relative_to(project_root).as_posix())
            if not directories:
                raise ContractError(f"No transcripts were imported from {source}")
            imports.append(directories)
            write_json(checkpoint, imports)
        directories = [directory for group in imports for directory in group]
        for directory in directories:
            if not (project_root / directory / "transcript.txt").exists():
                raise ContractError(f"Saved transcript is missing: {project_root / directory}")
        if not read_json(project_root / "project.json")["units"]:
            update_project(project_root, phase="transcript")
        return directories

    def _transform_knowledge(
        self,
        agent: CodexAgent,
        *,
        skill: str,
        stage: str,
        input_path: Path,
        target_seconds: int,
        feedback_path: Path | None = None,
    ) -> tuple[dict, Path]:
        feedback = f"Also address the review at {feedback_path}." if feedback_path else ""
        return agent.run(
            stage=stage,
            skill=skill,
            schema="knowledge",
            prompt=f"""Transform the knowledge model at {input_path} for a target narration duration of {target_seconds} seconds.
Preserve its kind and provenance. Return the transformed knowledge model only. {feedback}""",
        )

    def _format_knowledge(
        self,
        agent: CodexAgent,
        *,
        format_name: str,
        input_path: Path,
        target_seconds: int,
        feedback_path: Path | None = None,
    ) -> tuple[dict, Path]:
        feedback = f"Also address the review at {feedback_path}." if feedback_path else ""
        return agent.run(
            stage=f"format-{format_name}",
            skill=format_name,
            schema="knowledge",
            prompt=f"""Shape the knowledge model at {input_path} into the {format_name} format for approximately {target_seconds} seconds.
Set narrative.format to {format_name}. Preserve factual content and provenance. Do not write narration. {feedback}""",
        )

    def _plan(
        self,
        agent: CodexAgent,
        spec: CommandSpec,
        input_path: Path,
        target_seconds: int,
        feedback_path: Path | None = None,
    ) -> tuple[dict, Path]:
        feedback = f"Correct the issues in {feedback_path}." if feedback_path else ""
        return agent.run(
            stage="plan-script",
            skill="plan-script",
            schema="plan",
            prompt=f"""Plan a script from {input_path}.
Format: {spec.format}. Time controller: {spec.time_controller}. Target: {target_seconds} seconds.
The timed sum of hook and sections should closely match the target. Do not write narration. {feedback}""",
        )

    def _write(
        self,
        agent: CodexAgent,
        spec: CommandSpec,
        knowledge_path: Path,
        plan_path: Path,
        target_seconds: int,
        existing_script: Path | None = None,
        feedback_path: Path | None = None,
    ) -> tuple[dict, Path]:
        revision = ""
        if existing_script and feedback_path:
            revision = f"Revise the existing script at {existing_script} using the independent review at {feedback_path}."
        return agent.run(
            stage="write-script",
            skill="write-script",
            schema="script",
            prompt=f"""Write the final structured script from knowledge {knowledge_path} and plan {plan_path}.
Pipeline: {spec.pipeline}. Format: {spec.format}. Time controller: {spec.time_controller}. Target: {target_seconds} seconds.
Use original, natural spoken PT-BR and introduce no facts absent from the knowledge model. {revision}""",
        )

    def _review(
        self,
        agent: CodexAgent,
        spec: CommandSpec,
        knowledge_path: Path,
        plan_path: Path,
        script_path: Path,
        target_seconds: int,
    ) -> tuple[dict, Path]:
        return agent.run(
            stage="review-script",
            skill="review-script",
            schema="review",
            prompt=f"""Independently review script {script_path} against knowledge {knowledge_path} and plan {plan_path}.
Expected format: {spec.format}. Expected duration: {target_seconds} seconds.
Return findings only; do not rewrite the script.""",
        )

    def _produce_script(
        self,
        agent: CodexAgent,
        spec: CommandSpec,
        unit_dir: Path,
        pipeline_knowledge: dict,
    ) -> ApprovedScript | None:
        state = unit_dir / ".obscript"
        approved_path = state / "approved-script.json"
        if spec.project_id and approved_path.exists() and (state / "review.json").exists():
            script = read_json(approved_path)
            if read_json(state / "review.json")["verdict"] == "pass":
                for name in ["knowledge.json", "plan.json"]:
                    if not (state / name).exists():
                        raise ContractError(f"Approved script checkpoint is incomplete: {state / name}")
                receipt = state / "approved-inputs.json"
                if not receipt.exists() or read_json(receipt) != self._approval_inputs(unit_dir, pipeline_knowledge):
                    raise ContractError("Approved script inputs changed; restore the approved checkpoint before resuming")
                if not (unit_dir / "script.md").exists():
                    (unit_dir / "script.md").write_text(render_script(script), encoding="utf-8")
                return ApprovedScript(script, approved_path, state / "knowledge.json",
                                      state / "plan.json", state / "review.json",
                                      script["metadata"]["target_duration_seconds"])
        invalidate_downstream(unit_dir, "script")
        state = unit_dir / ".obscript"
        state.mkdir(parents=True, exist_ok=True)
        pipeline_path = state / "pipeline-knowledge.json"
        write_json(pipeline_path, pipeline_knowledge)
        target_seconds = choose_target_duration(
            pipeline_knowledge, spec.time_controller, spec.target_duration_seconds
        )

        timed_knowledge = pipeline_knowledge
        timed_path = pipeline_path
        if spec.time_controller in {"compress", "extend"}:
            timed_knowledge, timed_path = self._transform_knowledge(
                agent,
                skill=spec.time_controller,
                stage=spec.time_controller,
                input_path=pipeline_path,
                target_seconds=target_seconds,
            )

        formatted_knowledge = timed_knowledge
        formatted_path = timed_path
        if spec.format in {"topics", "essay"}:
            formatted_knowledge, formatted_path = self._format_knowledge(
                agent,
                format_name=spec.format,
                input_path=timed_path,
                target_seconds=target_seconds,
            )
        write_yaml(unit_dir / "knowledge.yaml", formatted_knowledge)

        plan, plan_path = self._plan(agent, spec, formatted_path, target_seconds)
        (unit_dir / "plan.md").write_text(render_plan(plan), encoding="utf-8")
        script, script_path = self._write(
            agent, spec, formatted_path, plan_path, target_seconds
        )
        (unit_dir / "script.md").write_text(render_script(script), encoding="utf-8")

        final_review: dict = {}
        review_path: Path | None = None
        for review_number in range(1, self.config.review_passes + 1):
            final_review, review_path = self._review(
                agent, spec, formatted_path, plan_path, script_path, target_seconds
            )
            write_yaml(unit_dir / "review.yaml", final_review)
            if final_review["verdict"] == "pass":
                if script["metadata"]["target_duration_seconds"] != target_seconds:
                    raise ContractError("approved script target differs from planned duration")
                approved_path = state / "approved-script.json"
                knowledge_path = state / "knowledge.json"
                approved_plan_path = state / "plan.json"
                approved_review_path = state / "review.json"
                write_json(approved_path, script)
                write_json(knowledge_path, formatted_knowledge)
                write_json(approved_plan_path, plan)
                write_json(approved_review_path, final_review)
                write_json(state / "approved-inputs.json", self._approval_inputs(unit_dir, pipeline_knowledge))
                return ApprovedScript(script, approved_path, knowledge_path, approved_plan_path, approved_review_path, target_seconds)
            if review_number == self.config.review_passes:
                break

            rerun = set(final_review.get("recommendation", {}).get("rerun", []))
            upstream_changed = False
            if spec.time_controller in rerun:
                timed_knowledge, timed_path = self._transform_knowledge(
                    agent,
                    skill=spec.time_controller,
                    stage=f"revise-{spec.time_controller}",
                    input_path=pipeline_path,
                    target_seconds=target_seconds,
                    feedback_path=review_path,
                )
                upstream_changed = True
            if spec.format in rerun or (upstream_changed and spec.format in {"topics", "essay"}):
                formatted_knowledge, formatted_path = self._format_knowledge(
                    agent,
                    format_name=spec.format,
                    input_path=timed_path,
                    target_seconds=target_seconds,
                    feedback_path=review_path,
                )
                upstream_changed = True
            elif upstream_changed:
                formatted_knowledge, formatted_path = timed_knowledge, timed_path
            if upstream_changed:
                write_yaml(unit_dir / "knowledge.yaml", formatted_knowledge)
            if upstream_changed or "plan-script" in rerun:
                plan, plan_path = self._plan(
                    agent, spec, formatted_path, target_seconds, review_path
                )
                (unit_dir / "plan.md").write_text(render_plan(plan), encoding="utf-8")
            script, script_path = self._write(
                agent,
                spec,
                formatted_path,
                plan_path,
                target_seconds,
                existing_script=script_path,
                feedback_path=review_path,
            )
            (unit_dir / "script.md").write_text(render_script(script), encoding="utf-8")
        return None

    def _approval_inputs(self, unit_dir: Path, pipeline_knowledge: dict) -> dict:
        return {
            "files": {name: file_sha256(unit_dir / ".obscript" / name)
                      for name in ["approved-script.json", "knowledge.json", "plan.json", "review.json"]},
            "pipeline_knowledge": hashlib.sha256(json.dumps(pipeline_knowledge, sort_keys=True,
                                                            ensure_ascii=False).encode()).hexdigest(),
        }

    def _get_storybook(
        self, agent: CodexAgent, unit_dir: Path, approved: ApprovedScript,
        direction_path: Path, *, render: bool = False,
    ) -> tuple[dict, Path]:
        path = unit_dir / "storybook.yaml"
        reference = unit_dir / ".obscript/creative-direction-source.json"
        if path.exists():
            expected = creative_direction_reference(direction_path, read_creative_direction(direction_path))
            if not reference.exists() or read_json(reference) != expected:
                # An explicit storybook request can rebuild plans after standards change.
                # Rendering must never silently replace a manually edited plan.
                if not render:
                    invalidate_downstream(unit_dir, "creative-direction")
                    return self._create_storybook(agent, unit_dir, approved, direction_path)
                raise ContractError("Shared creative direction changed after storybook planning; run PROJECT_ID --storybook before rendering")
            storybook = read_yaml(path)
            self._validate_storybook(approved, storybook)
            previous_path = unit_dir / ".obscript/storybook.json"
            if previous_path.exists():
                previous = read_json(previous_path)
                direction_link = Path(os.path.relpath(direction_path, unit_dir))
                for name, old, new in [
                    ("script.md", render_script(approved.script, previous), render_script(approved.script, storybook)),
                    ("storybook.md", render_storybook(previous, approved.script, direction_path=direction_link),
                     render_storybook(storybook, approved.script, direction_path=direction_link)),
                ]:
                    document = unit_dir / name
                    if not document.exists() or document.read_text(encoding="utf-8") == old:
                        if old != new or not document.exists():
                            document.write_text(new, encoding="utf-8")
                if previous != storybook:
                    write_json(previous_path, storybook)
            return storybook, path
        return self._create_storybook(agent, unit_dir, approved, direction_path)

    def _create_storybook(
        self, agent: CodexAgent, unit_dir: Path, approved: ApprovedScript,
        direction_path: Path,
    ) -> tuple[dict, Path]:
        invalidate_downstream(unit_dir, "storybook")
        (unit_dir / "script.md").write_text(render_script(approved.script), encoding="utf-8")
        feedback = ""
        direction = read_creative_direction(direction_path)
        direction_link = Path(os.path.relpath(direction_path, unit_dir))
        # A bounded retry prevents endless planning; all attempts and errors remain inspectable.
        for attempt in range(1, 4):
            storybook, _ = agent.run(
                stage=f"storybook-{attempt:02d}", skill="storybook", schema="storybook",
                prompt=f"""Create the complete storybook from approved structured script {approved.script_path},
shared creative direction {direction_path}, and plan {approved.plan_path}.
The shared Markdown is the single source of truth for visual standards. Honor every filled field.
Blank fields and template suggestions are unspecified, not instructions to invent a new identity.
Resolve unspecified execution details only in scene specifications. Never create or edit a creative-direction file.
Approval: {approved.review_path}. Target: {approved.target_seconds} seconds.
Cover every narration word exactly once in original section order, as contiguous exact excerpts.
No scene may span sections. Timing starts at zero, is continuous, and ends at the target.
Production is silent animations only. Narration excerpts are timing references for a human reader.
Write scene and production directions in English; preserve narration verbatim and keep on-screen labels in the script's language unless shared direction specifies otherwise.
Describe visible elements, positions, asset references, backgrounds, and timed motion, without re-explaining the narration.
Make each render_brief a concise, self-contained imperative paragraph covering the complete scene and its transition.
Use supplied asset paths exactly; identify assets needing sourcing or creation instead of inventing existing files.
Do not request audio, TTS, music, sound effects, or automatic subtitles. Scene timestamps govern rendering.
Do not rewrite narration, invoke HyperFrames, or generate media. {feedback}""",
            )
            try:
                self._validate_storybook(approved, storybook)
            except ContractError as exc:
                (unit_dir / "storybook.md").write_text(
                    render_storybook(storybook, approved.script, direction_path=direction_link, validation_error=str(exc)), encoding="utf-8",
                )
                error_path = unit_dir / ".obscript" / f"storybook-{attempt:02d}.validation.json"
                write_json(error_path, {"status": "invalid", "error": str(exc)})
                feedback = f"Previous attempt was rejected by application validation: {exc}. Correct this defect and return the complete storybook."
                if attempt == 3:
                    raise ContractError(f"Storybook remained invalid after 3 attempts: {exc}; inspect {unit_dir / 'storybook.md'}") from exc
                continue
            path = unit_dir / ".obscript/storybook.json"
            if read_creative_direction(direction_path) != direction:
                raise ContractError("Shared creative direction changed during storybook planning; rerun to rebuild the scene plan")
            write_json(unit_dir / ".obscript/creative-direction-source.json", creative_direction_reference(direction_path, direction))
            write_json(path, storybook)
            write_yaml(unit_dir / "storybook.yaml", storybook)
            (unit_dir / "storybook.md").write_text(render_storybook(storybook, approved.script, direction_path=direction_link), encoding="utf-8")
            (unit_dir / "script.md").write_text(render_script(approved.script, storybook), encoding="utf-8")
            return storybook, unit_dir / "storybook.yaml"
        raise AssertionError("unreachable")

    def _validate_storybook(self, approved: ApprovedScript, storybook: dict) -> None:
        validate_storybook(approved.script, storybook, approved.target_seconds)

    def _produce_video(
        self, unit_dir: Path, approved: ApprovedScript, direction_path: Path, storybook_path: Path,
    ) -> Path:
        receipt_path = unit_dir / ".obscript/production-inputs.json"
        inputs = {str(path.relative_to(unit_dir)) if path.is_relative_to(unit_dir) else str(path):
                  file_sha256(path)
                  for path in [approved.script_path, approved.review_path, direction_path, storybook_path]}
        video = unit_dir / "video.mp4"
        if receipt_path.exists() and video.exists() and (unit_dir / "production.yaml").exists():
            receipt = read_json(receipt_path)
            if (receipt.get("inputs") == inputs and read_yaml(unit_dir / "production.yaml").get("status") == "complete"
                    and receipt.get("video_sha256") == file_sha256(video)):
                return video
        result = ProductionAgent(self.config, unit_dir).produce(
            script_path=approved.script_path, direction_path=direction_path,
            storybook_path=storybook_path, review_path=approved.review_path,
        )
        write_json(receipt_path, {"inputs": inputs, "video_sha256": file_sha256(result)})
        return result
