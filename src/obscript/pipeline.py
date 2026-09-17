from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .codex_agent import CodexAgent
from .contracts import ContractError, choose_target_duration
from .models import CommandSpec, RuntimeConfig, SourceAsset
from .production import ProductionAgent, invalidate_downstream, validate_storybook, validate_structure
from .storage import (
    copy_if_present,
    read_json,
    render_creative_direction,
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
        assets: list[SourceAsset] = []
        for source in spec.sources:
            print(f"[obscript] preparando fonte: {source}", flush=True)
            assets.extend(
                ingest_source(
                    source,
                    ytstt=self.config.ytstt,
                    transcripts_dir=self.config.transcripts_dir,
                )
            )
        if spec.pipeline == "remix" and len(assets) < 2:
            raise ContractError("remix requires at least two videos after source expansion")
        if spec.pipeline == "split" and len(assets) != 1:
            raise ContractError("split requires one video, but the source expanded to a playlist")

        name = self.config.project_name or assets[0].title
        project_root = unique_directory(
            self.config.output_dir,
            slugify(name, datetime.now().strftime("video-%Y%m%d-%H%M%S")),
        )
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
                "created_at": datetime.now().astimezone().isoformat(),
                "pipeline": spec.pipeline,
                "time_controller": spec.time_controller,
                "format": spec.format,
                "target_duration_seconds": spec.target_duration_seconds,
                "split_count": spec.split_count,
                "render": spec.render,
                "sources": list(spec.sources),
                "agent": "Codex CLI",
                "model": self.config.model or "configured default",
                "reasoning_effort": self.config.reasoning_effort,
            },
        )

        analyses: list[dict] = []
        for index, asset in enumerate(assets, 1):
            source_dir = project_root / "sources" / f"source-{index:02d}-{slugify(asset.title)}"
            source_dir.mkdir(parents=True)
            transcript_txt = copy_if_present(asset.transcript_txt, source_dir / "transcript.txt")
            transcript_srt = copy_if_present(asset.transcript_srt, source_dir / "transcript.srt")
            transcript_json = copy_if_present(asset.transcript_json, source_dir / "transcript.json")
            source_manifest = {
                "id": f"source-{index:02d}",
                "title": asset.title,
                "source": asset.original,
                "language": asset.language,
                "duration_seconds": round(asset.duration_seconds, 3),
                "transcript_txt": str(transcript_txt),
                "transcript_srt": str(transcript_srt) if transcript_srt else None,
                "transcript_json": str(transcript_json) if transcript_json else None,
            }
            write_json(source_dir / "source.json", source_manifest)
            analysis, analysis_path = agent.run(
                stage=f"analyze-source-{index:02d}",
                skill="analyze-source",
                schema="knowledge",
                prompt=f"""Analyze the transcript at {transcript_txt}.
Source metadata is at {source_dir / 'source.json'}.
Create a canonical PT-BR knowledge model. Set kind to single and narrative.format to source.
Use stable topic IDs prefixed with source-{index:02d}/. Preserve factual qualifications and do not write narration.""",
            )
            analyses.append(analysis)
            write_yaml(source_dir / "analysis.yaml", analysis)
            print(f"[obscript] análise: {analysis_path}", flush=True)

        if spec.pipeline == "remix":
            analyses_path = project_root / ".obscript" / "source-analyses.json"
            write_json(analyses_path, analyses)
            knowledge, _ = agent.run(
                stage="remix",
                skill="remix",
                schema="knowledge",
                prompt=f"""Merge every knowledge model in {analyses_path} into one genuinely unified model.
Set kind to remix. Deduplicate overlap, preserve provenance in source_refs, surface unresolved contradictions, and create a new defensible thesis.""",
            )
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
            split_result, _ = agent.run(
                stage="split",
                skill="split",
                schema="split",
                prompt=f"""Split the knowledge model at {knowledge_path} semantically, never by equal transcript intervals.
{count_instruction}
{target_instruction}
Each part must be a complete knowledge model with kind split and narrative.format source.""",
            )
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
                _, direction_path = self._create_creative_direction(unit_agent, spec, unit_dir, approved)
                storybook, storybook_path = self._create_storybook(unit_agent, unit_dir, approved, direction_path)
                outputs.extend([unit_dir / "creative-direction.md", unit_dir / "storybook.md", unit_dir / "storybook.yaml"])
                if spec.render:
                    outputs.append(self._produce_video(unit_dir, approved, direction_path, storybook_path))
                    outputs.append(unit_dir / "production.yaml")
        return PipelineResult(project_root, tuple(outputs), all_passed)

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

    def _create_creative_direction(
        self, agent: CodexAgent, spec: CommandSpec, unit_dir: Path, approved: ApprovedScript,
    ) -> tuple[dict, Path]:
        invalidate_downstream(unit_dir, "creative-direction")
        (unit_dir / "script.md").write_text(render_script(approved.script), encoding="utf-8")
        direction, _ = agent.run(
            stage="creative-direction", skill="creative-direction", schema="creative-direction",
            prompt=f"""Establish one original visual identity from knowledge {approved.knowledge_path},
plan {approved.plan_path}, and approved structured script {approved.script_path}.
Approval: {approved.review_path}. Target: {approved.target_seconds} seconds.
Format: {spec.format}. Pipeline: {spec.pipeline}.
Commit to one direction in every field, with no alternatives. Narration is immutable.
Specify silent animations only; a human will record and handle all audio outside this pipeline.
Use supporting on-screen text without automatic subtitles.
Do not reproduce the source video's identity. Do not invoke HyperFrames or generate media.""",
        )
        validate_structure(direction, read_json(self.config.repo_root / "schemas/creative-direction.schema.json"))
        path = unit_dir / ".obscript/creative-direction.json"
        write_json(path, direction)
        (unit_dir / "creative-direction.md").write_text(render_creative_direction(direction), encoding="utf-8")
        return direction, path

    def _create_storybook(
        self, agent: CodexAgent, unit_dir: Path, approved: ApprovedScript,
        direction_path: Path,
    ) -> tuple[dict, Path]:
        invalidate_downstream(unit_dir, "storybook")
        (unit_dir / "script.md").write_text(render_script(approved.script), encoding="utf-8")
        feedback = ""
        # A bounded retry prevents endless planning; all attempts and errors remain inspectable.
        for attempt in range(1, 4):
            storybook, _ = agent.run(
                stage=f"storybook-{attempt:02d}", skill="storybook", schema="storybook",
                prompt=f"""Create the complete storybook from approved structured script {approved.script_path},
creative direction {direction_path}, and plan {approved.plan_path}.
Approval: {approved.review_path}. Target: {approved.target_seconds} seconds.
Cover every narration word exactly once in original section order, as contiguous exact excerpts.
No scene may span sections. Timing starts at zero, is continuous, and ends at the target.
Production is silent animations only. Narration excerpts are timing references for a human reader.
Do not request audio, TTS, music, sound effects, or automatic subtitles. Scene timestamps govern rendering.
Do not rewrite narration, invoke HyperFrames, or generate media. {feedback}""",
            )
            try:
                self._validate_storybook(approved, storybook)
            except ContractError as exc:
                (unit_dir / "storybook.md").write_text(
                    render_storybook(storybook, approved.script, validation_error=str(exc)), encoding="utf-8",
                )
                error_path = unit_dir / ".obscript" / f"storybook-{attempt:02d}.validation.json"
                write_json(error_path, {"status": "invalid", "error": str(exc)})
                feedback = f"Previous attempt was rejected by application validation: {exc}. Correct this defect and return the complete storybook."
                if attempt == 3:
                    raise ContractError(f"Storybook remained invalid after 3 attempts: {exc}; inspect {unit_dir / 'storybook.md'}") from exc
                continue
            path = unit_dir / ".obscript/storybook.json"
            write_json(path, storybook)
            write_yaml(unit_dir / "storybook.yaml", storybook)
            (unit_dir / "storybook.md").write_text(render_storybook(storybook, approved.script), encoding="utf-8")
            (unit_dir / "script.md").write_text(render_script(approved.script, storybook), encoding="utf-8")
            return storybook, unit_dir / "storybook.yaml"
        raise AssertionError("unreachable")

    def _validate_storybook(self, approved: ApprovedScript, storybook: dict) -> None:
        validate_storybook(approved.script, storybook, approved.target_seconds)

    def _produce_video(
        self, unit_dir: Path, approved: ApprovedScript, direction_path: Path, storybook_path: Path,
    ) -> Path:
        return ProductionAgent(self.config, unit_dir).produce(
            script_path=approved.script_path, direction_path=direction_path,
            storybook_path=storybook_path, review_path=approved.review_path,
        )
