"""Command-line entrypoint for the Multimodal 236722 pipeline."""

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Annotated

import typer

from multimodal_bias import __version__
from multimodal_bias.arbitration import (
    arbitrate_final_predictions,
    read_verification_artifact,
)
from multimodal_bias.candidate_harness import (
    load_candidate_manifest,
    run_candidate_smoke,
    write_candidate_report,
)
from multimodal_bias.config import DEFAULT_CONFIG_PATH, load_config
from multimodal_bias.data_loader import (
    DEFAULT_DATA_ROOT,
    load_test_records,
    validate_data_layout,
)
from multimodal_bias.exceptions import (
    CandidateEligibilityError,
    ConfigurationError,
    DataLayoutError,
    InferenceError,
    ModelLoadError,
    ParseError,
    ShadowValidationError,
    SubmissionFormatError,
)
from multimodal_bias.models.adapter import (
    DEFAULT_MODEL_CONFIG_PATH,
    create_model_adapter,
    load_model_config,
)
from multimodal_bias.parsing import (
    parse_reasoner_artifact,
    read_parsed_reasoner_artifact,
)
from multimodal_bias.prompting.guards import REASONER_PROMPT_SCHEMA_MODES
from multimodal_bias.prompting.templates import (
    DEFAULT_REASONER_PROMPT_PATH,
    DEFAULT_VERIFIER_PROMPT_PATH,
)
from multimodal_bias.reasoner import (
    RAW_REASONER_PARTIAL_FILENAME,
    prepare_reasoner_inference,
    run_reasoner_inference,
)
from multimodal_bias.run_logging import start_run
from multimodal_bias.schemas import ModelGenerationRequest
from multimodal_bias.shadow_acquisition import (
    acquire_shadow_metadata,
    build_shadow_candidate_pool,
    download_shadow_candidate_images,
    generate_pending_shadow_records,
)
from multimodal_bias.shadow_review import apply_shadow_reviews
from multimodal_bias.submission import (
    generate_submission_artifacts,
    generate_submission_artifacts_from_predictions,
    resolve_run_directory,
)
from multimodal_bias.validation import (
    audit_shadow_records,
    evaluate_shadow_predictions,
    freeze_shadow_dataset,
    load_shadow_records,
    write_audit_report,
)
from multimodal_bias.verifier import run_conditional_verification

app = typer.Typer(
    help="Multimodal 236722 offline multimodal AI bias competition pipeline.",
    invoke_without_command=True,
    no_args_is_help=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"multimodal-bias {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show package version and exit.",
    ),
) -> None:
    """Run the Multimodal 236722 command-line application."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


@app.command("validate-data")
def validate_data(
    data_root: Annotated[
        Path,
        typer.Option(
            "--data-root",
            help="Path to the extracted official Multimodal open directory.",
        ),
    ] = DEFAULT_DATA_ROOT,
) -> None:
    """Validate the official Multimodal data layout before inference."""
    try:
        report = validate_data_layout(data_root)
    except DataLayoutError as exc:
        typer.echo(f"Data layout invalid: {exc}", err=True)
        raise typer.Exit(1) from None

    typer.echo(
        "Data layout valid: "
        f"root={report.data_root} "
        f"train_rows={report.train_rows} "
        f"test_rows={report.test_rows} "
        f"sample_submission_rows={report.sample_submission_rows}"
    )


@app.command("start-run")
def start_run_command(
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            help="Path to the runtime YAML config file.",
        ),
    ] = DEFAULT_CONFIG_PATH,
) -> None:
    """Create a reproducible run directory and base metadata artifacts."""

    try:
        runtime_config = load_config(config)
        manifest = start_run(runtime_config, config_path=config)
    except ConfigurationError as exc:
        typer.echo(f"Config invalid: {exc}", err=True)
        raise typer.Exit(1) from None
    except OSError as exc:
        typer.echo(f"Run could not be started: {exc}", err=True)
        raise typer.Exit(1) from None

    typer.echo(f"Run started: run_id={manifest.run_id} run_dir={manifest.run_dir}")


@app.command("infer")
def infer(
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            help="Path to the runtime YAML config file.",
        ),
    ] = DEFAULT_CONFIG_PATH,
    model_config: Annotated[
        Path,
        typer.Option(
            "--model-config",
            help="Path to a local model adapter YAML config.",
        ),
    ] = DEFAULT_MODEL_CONFIG_PATH,
    prompt_template: Annotated[
        Path,
        typer.Option(
            "--prompt-template",
            help="Path to the versioned Reasoner prompt template YAML file.",
        ),
    ] = DEFAULT_REASONER_PROMPT_PATH,
) -> None:
    """Run first-pass Reasoner inference and preserve raw model output."""

    try:
        runtime_config = load_config(config)
    except ConfigurationError as exc:
        typer.echo(f"Config invalid: {exc}", err=True)
        raise typer.Exit(1) from None

    try:
        model_settings = load_model_config(model_config)
    except ConfigurationError as exc:
        typer.echo(f"Model config invalid: {exc}", err=True)
        raise typer.Exit(1) from None

    try:
        prepared = prepare_reasoner_inference(
            runtime_config,
            model_settings,
            prompt_template_path=prompt_template,
        )
        manifest = start_run(runtime_config, config_path=config)
        typer.echo(
            "Inference started: "
            f"run_id={manifest.run_id} "
            f"run_dir={manifest.run_dir} "
            f"partial_raw_reasoner_path={manifest.run_dir / RAW_REASONER_PARTIAL_FILENAME}"
        )
        result = run_reasoner_inference(
            runtime_config,
            model_settings,
            manifest,
            prompt_template_path=prompt_template,
            prepared=prepared,
        )
        parse_result = parse_reasoner_artifact(
            result.raw_reasoner_path,
            expected_run_id=result.manifest.run_id,
            expected_sample_ids=tuple(record.sample_id for record in prepared.records),
            schema_mode=REASONER_PROMPT_SCHEMA_MODES[prepared.prompt_version],
        )
    except DataLayoutError as exc:
        typer.echo(f"Data layout invalid: {exc}", err=True)
        raise typer.Exit(1) from None
    except ConfigurationError as exc:
        typer.echo(f"Inference config invalid: {exc}", err=True)
        raise typer.Exit(1) from None
    except ModelLoadError as exc:
        typer.echo(f"Model load failed: {exc}", err=True)
        raise typer.Exit(1) from None
    except InferenceError as exc:
        typer.echo(f"Inference failed: {exc}", err=True)
        raise typer.Exit(1) from None
    except ParseError as exc:
        typer.echo(f"Reasoner parsing failed: {exc}", err=True)
        raise typer.Exit(1) from None
    except OSError as exc:
        typer.echo(f"Inference artifacts could not be written: {exc}", err=True)
        raise typer.Exit(1) from None

    typer.echo(
        "Inference complete: "
        f"run_id={result.manifest.run_id} "
        f"run_dir={result.manifest.run_dir} "
        f"raw_reasoner_path={result.raw_reasoner_path} "
        f"parsed_reasoner_path={parse_result.parsed_reasoner_path} "
        f"total_samples={result.total_samples} "
        f"generated={result.generated_count} "
        f"failures={result.failure_count} "
        f"parsed_valid={parse_result.valid_count} "
        f"parsed_invalid={parse_result.invalid_count}"
    )


@app.command("smoke-model")
def smoke_model(
    model_config: Annotated[
        Path,
        typer.Option(
            "--model-config",
            help="Path to a local model adapter YAML config.",
        ),
    ] = DEFAULT_MODEL_CONFIG_PATH,
    prompt: Annotated[
        str,
        typer.Option(
            "--prompt",
            help="Short prompt for one local model smoke generation.",
        ),
    ] = "Return a concise local model smoke-test response.",
    image_path: Annotated[
        Path | None,
        typer.Option(
            "--image-path",
            help="Optional local image path for VLM smoke generation.",
        ),
    ] = None,
) -> None:
    """Smoke-test a local VLM adapter and emit raw output metadata as JSON."""

    try:
        config = load_model_config(model_config)
        adapter = create_model_adapter(config)
        load_metadata = adapter.load()
        result = adapter.generate(
            ModelGenerationRequest(prompt_text=prompt, image_path=image_path),
        )
    except ConfigurationError as exc:
        typer.echo(f"Model config invalid: {exc}", err=True)
        raise typer.Exit(1) from None
    except ModelLoadError as exc:
        typer.echo(f"Model load failed: {exc}", err=True)
        raise typer.Exit(1) from None
    except InferenceError as exc:
        typer.echo(f"Model inference failed: {exc}", err=True)
        raise typer.Exit(1) from None

    typer.echo(
        json.dumps(
            {
                "load": _jsonable(load_metadata),
                "generation": _jsonable(result.metadata),
                "raw_text": result.raw_text,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


@app.command("candidate-smoke")
def candidate_smoke(
    candidate_manifest: Annotated[
        Path, typer.Option("--candidate-manifest", help="Strict candidate eligibility YAML.")
    ],
    model_config: Annotated[
        Path, typer.Option("--model-config", help="Local model adapter YAML config.")
    ],
    image_path: Annotated[
        Path, typer.Option("--image-path", help="One real local image for Reasoner v3 smoke.")
    ],
    output: Annotated[
        Path, typer.Option("--output", help="No-clobber candidate smoke JSON report path.")
    ],
) -> None:
    """Gate one candidate before diagnostic-48 evaluation."""

    try:
        manifest = load_candidate_manifest(candidate_manifest)
        settings = load_model_config(model_config)
        report = run_candidate_smoke(manifest, settings, image_path)
        report_path = write_candidate_report(report, output)
    except CandidateEligibilityError as exc:
        typer.echo(json.dumps({"code": exc.code, "error": str(exc)}, sort_keys=True), err=True)
        raise typer.Exit(1) from None
    except ConfigurationError as exc:
        typer.echo(f"Candidate model config invalid: {exc}", err=True)
        raise typer.Exit(1) from None

    typer.echo(
        "Candidate smoke complete: "
        f"candidate_id={report.candidate_id} "
        f"diagnostic_48_allowed={str(report.diagnostic_48_allowed).lower()} "
        f"report={report_path}"
    )
    if not report.diagnostic_48_allowed:
        raise typer.Exit(1)


@app.command("make-submission")
def make_submission(
    run_id: Annotated[
        str,
        typer.Option(
            "--run-id",
            help="Run identifier beneath the configured runs root.",
        ),
    ] = ...,
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            help="Path to the runtime YAML config file.",
        ),
    ] = DEFAULT_CONFIG_PATH,
    use_verification: Annotated[
        bool,
        typer.Option(
            "--use-verification",
            help="Use verification.jsonl and final-label arbitration before submission.",
        ),
    ] = False,
) -> None:
    """Generate validated final predictions and the Multimodal submission CSV."""

    try:
        runtime_config = load_config(config)
        run_dir = resolve_run_directory(runtime_config.runs_root, run_id)
        records = load_test_records(runtime_config.data_root)
        expected_sample_ids = tuple(record.sample_id for record in records)
        if use_verification:
            reasoner_records = read_parsed_reasoner_artifact(
                run_dir / "parsed_reasoner.csv",
                expected_run_id=run_id,
                expected_sample_ids=expected_sample_ids,
            )
            verification_records = read_verification_artifact(
                run_dir / "verification.jsonl",
                expected_run_id=run_id,
                expected_sample_ids=expected_sample_ids,
            )
            predictions = arbitrate_final_predictions(reasoner_records, verification_records)
            result = generate_submission_artifacts_from_predictions(
                predictions,
                run_dir,
                expected_run_id=run_id,
                expected_sample_ids=expected_sample_ids,
            )
        else:
            result = generate_submission_artifacts(
                run_dir / "parsed_reasoner.csv",
                run_dir,
                expected_run_id=run_id,
                expected_sample_ids=expected_sample_ids,
            )
    except ConfigurationError as exc:
        typer.echo(f"Config invalid: {exc}", err=True)
        raise typer.Exit(1) from None
    except DataLayoutError as exc:
        typer.echo(f"Data layout invalid: {exc}", err=True)
        raise typer.Exit(1) from None
    except SubmissionFormatError as exc:
        typer.echo(f"Submission invalid: {exc}", err=True)
        raise typer.Exit(1) from None
    except ParseError as exc:
        typer.echo(f"Submission invalid: {exc}", err=True)
        raise typer.Exit(1) from None
    except OSError as exc:
        typer.echo(f"Submission artifacts could not be written: {exc}", err=True)
        raise typer.Exit(1) from None

    typer.echo(
        "Submission complete: "
        f"run_id={run_id} "
        f"final_predictions_path={result.final_predictions_path} "
        f"submission_path={result.submission_path} "
        f"total_samples={result.total_samples}"
    )


@app.command("verify-risky")
def verify_risky(
    run_id: Annotated[
        str,
        typer.Option(
            "--run-id",
            help="Run identifier beneath the configured runs root.",
        ),
    ] = ...,
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            help="Path to the runtime YAML config file.",
        ),
    ] = DEFAULT_CONFIG_PATH,
    model_config: Annotated[
        Path,
        typer.Option(
            "--model-config",
            help="Path to a local model adapter YAML config.",
        ),
    ] = DEFAULT_MODEL_CONFIG_PATH,
    prompt_template: Annotated[
        Path,
        typer.Option(
            "--prompt-template",
            help="Path to the versioned Verifier prompt template YAML file.",
        ),
    ] = DEFAULT_VERIFIER_PROMPT_PATH,
) -> None:
    """Run the local Verifier only for triggered Reasoner predictions."""

    try:
        runtime_config = load_config(config)
        model_settings = load_model_config(model_config)
        run_dir = resolve_run_directory(runtime_config.runs_root, run_id)
        samples = load_test_records(runtime_config.data_root, allow_missing_images=True)
        records = read_parsed_reasoner_artifact(
            run_dir / "parsed_reasoner.csv",
            expected_run_id=run_id,
            expected_sample_ids=tuple(sample.sample_id for sample in samples),
        )
        result = run_conditional_verification(
            records,
            samples,
            run_dir,
            model_settings,
            prompt_template_path=prompt_template,
        )
    except ConfigurationError as exc:
        typer.echo(f"Verification config invalid: {exc}", err=True)
        raise typer.Exit(1) from None
    except DataLayoutError as exc:
        typer.echo(f"Data layout invalid: {exc}", err=True)
        raise typer.Exit(1) from None
    except SubmissionFormatError as exc:
        typer.echo(f"Verification invalid: {exc}", err=True)
        raise typer.Exit(1) from None
    except ModelLoadError as exc:
        typer.echo(f"Verifier model load failed: {exc}", err=True)
        raise typer.Exit(1) from None
    except InferenceError as exc:
        typer.echo(f"Verification inference failed: {exc}", err=True)
        raise typer.Exit(1) from None
    except ParseError as exc:
        typer.echo(f"Verification invalid: {exc}", err=True)
        raise typer.Exit(1) from None
    except OSError as exc:
        typer.echo(f"Verification artifact could not be written: {exc}", err=True)
        raise typer.Exit(1) from None

    typer.echo(
        "Verification complete: "
        f"run_id={run_id} "
        f"verification_path={result.verification_path} "
        f"total_samples={result.total_samples} "
        f"triggered={result.triggered_count} "
        f"verified={result.verified_count} "
        f"skipped={result.skipped_count} "
        f"failed={result.failed_count}"
    )


@app.command("shadow-audit")
def shadow_audit(
    dataset: Annotated[Path, typer.Option("--dataset", help="Independent Shadow JSONL.")],
    image_root: Annotated[Path, typer.Option("--image-root", help="Root for image_ref paths.")],
    output: Annotated[Path, typer.Option("--output", help="No-clobber audit JSON path.")],
) -> None:
    """Audit Shadow records, provenance, independent review, images, and coverage."""
    try:
        report = audit_shadow_records(load_shadow_records(dataset, image_root))
        write_audit_report(report, output)
    except (ShadowValidationError, OSError) as exc:
        typer.echo(f"Shadow audit failed: {exc}", err=True)
        raise typer.Exit(1) from None
    typer.echo(
        "Shadow audit complete: "
        f"records={report.record_count} reviewed={report.reviewed_count} "
        f"promotion_ready={str(report.promotion_ready).lower()} "
        f"violations={len(report.violations)} report={output}"
    )
    if not report.promotion_ready:
        raise typer.Exit(1)


@app.command("shadow-apply-reviews")
def shadow_apply_reviews(
    dataset: Annotated[Path, typer.Option("--dataset", help="Pending Shadow JSONL.")],
    image_root: Annotated[Path, typer.Option("--image-root", help="Root for image_ref paths.")],
    decisions: Annotated[
        Path, typer.Option("--decisions", help="Independent human review decision JSONL.")
    ],
    output_dir: Annotated[
        Path, typer.Option("--output-dir", help="New no-clobber review evidence directory.")
    ],
    adjudications: Annotated[
        Path | None,
        typer.Option("--adjudications", help="Optional independent adjudication JSONL."),
    ] = None,
) -> None:
    """Apply human Shadow reviews while preserving disputes, rejections, and hashes."""
    try:
        result = apply_shadow_reviews(
            dataset,
            image_root,
            decisions,
            output_dir,
            adjudications_path=adjudications,
        )
    except (ShadowValidationError, OSError) as exc:
        typer.echo(f"Shadow review application failed: {exc}", err=True)
        raise typer.Exit(1) from None
    typer.echo(
        "Shadow review application complete: "
        f"records={result.report.input_record_count} "
        f"decisions={result.report.decision_count} "
        f"reviewed={result.report.reviewed_count} "
        f"adjudicated={result.report.adjudicated_count} "
        f"rejected={result.report.rejected_count} "
        f"unresolved={result.report.unresolved_count} "
        f"promotion_ready={str(result.report.promotion_ready).lower()} "
        f"report={result.report_path}"
    )
    if not result.report.promotion_ready:
        raise typer.Exit(1)


@app.command("shadow-freeze")
def shadow_freeze(
    dataset: Annotated[Path, typer.Option("--dataset", help="Auditable Shadow JSONL.")],
    image_root: Annotated[Path, typer.Option("--image-root", help="Root for image_ref paths.")],
    output_dir: Annotated[Path, typer.Option("--output-dir", help="New immutable freeze dir.")],
    dataset_version: Annotated[str, typer.Option("--dataset-version", help="New version ID.")],
) -> None:
    """Freeze a complete, balanced, independently reviewed Shadow corpus."""
    try:
        result = freeze_shadow_dataset(dataset, image_root, output_dir, dataset_version)
    except (ShadowValidationError, OSError) as exc:
        typer.echo(f"Shadow freeze failed: {exc}", err=True)
        raise typer.Exit(1) from None
    typer.echo(
        "Shadow freeze complete: "
        f"version={result.dataset_version} records={result.record_count} "
        f"manifest_sha256={result.manifest_sha256} output_dir={result.output_dir}"
    )


@app.command("shadow-evaluate")
def shadow_evaluate(
    frozen_dir: Annotated[Path, typer.Option("--frozen-dir", help="Frozen dataset dir.")],
    predictions: Annotated[Path, typer.Option("--predictions", help="Ordered JSONL predictions.")],
    output: Annotated[Path, typer.Option("--output", help="New metrics JSON path.")],
    candidate_id: Annotated[str, typer.Option("--candidate-id", help="Candidate identity.")],
    split: Annotated[
        str, typer.Option("--split", help="selection or sealed_holdout.")
    ] = "selection",
) -> None:
    """Evaluate exact ordered predictions; sealed output is aggregate-only."""
    try:
        result = evaluate_shadow_predictions(
            frozen_dir,
            predictions,
            output,
            candidate_id,
            split,  # type: ignore[arg-type]
        )
    except (ShadowValidationError, OSError, ValueError) as exc:
        typer.echo(f"Shadow evaluation failed: {exc}", err=True)
        raise typer.Exit(1) from None
    typer.echo(
        "Shadow evaluation complete: "
        f"candidate_id={result.candidate_id} split={result.split} metrics={result.metrics_path}"
    )


@app.command("shadow-acquire-metadata")
def shadow_acquire_metadata(
    source_manifest: Annotated[
        Path, typer.Option("--source-manifest", help="Pinned official metadata source YAML.")
    ],
    output_dir: Annotated[
        Path, typer.Option("--output-dir", help="New no-clobber metadata acquisition directory.")
    ],
) -> None:
    """Download official Shadow source metadata and annotations, never image pixels."""
    try:
        manifest_path = acquire_shadow_metadata(source_manifest, output_dir)
    except (ShadowValidationError, OSError) as exc:
        typer.echo(f"Shadow metadata acquisition failed: {exc}", err=True)
        raise typer.Exit(1) from None
    typer.echo(f"Shadow metadata acquisition complete: manifest={manifest_path}")


@app.command("shadow-build-candidate-pool")
def shadow_build_candidate_pool(
    acquisition_dir: Annotated[
        Path, typer.Option("--acquisition-dir", help="Completed metadata acquisition directory.")
    ],
    output_dir: Annotated[
        Path, typer.Option("--output-dir", help="New no-clobber candidate-pool directory.")
    ],
    seed: Annotated[int, typer.Option("--seed", help="Deterministic selection seed.")] = 236722600,
) -> None:
    """Build 900 Open Images/MIAP and 300 VSR metadata candidates."""
    try:
        report_path = build_shadow_candidate_pool(acquisition_dir, output_dir, seed=seed)
    except (ShadowValidationError, OSError) as exc:
        typer.echo(f"Shadow candidate pool failed: {exc}", err=True)
        raise typer.Exit(1) from None
    typer.echo(f"Shadow candidate pool complete: report={report_path}")


@app.command("shadow-download-images")
def shadow_download_images(
    candidates: Annotated[
        Path, typer.Option("--candidates", help="Metadata-only candidate JSONL.")
    ],
    output_dir: Annotated[
        Path, typer.Option("--output-dir", help="New verified pending image-pool directory.")
    ],
    count: Annotated[int, typer.Option("--count", help="Number of accepted images.")] = 600,
    concurrency: Annotated[
        int, typer.Option("--concurrency", help="Parallel landing/pixel fetches.")
    ] = 16,
) -> None:
    """Verify attribution pages and download decodable Open Images candidates."""
    try:
        report_path = download_shadow_candidate_images(
            candidates, output_dir, count=count, concurrency=concurrency
        )
    except (ShadowValidationError, OSError) as exc:
        typer.echo(f"Shadow image download failed: {exc}", err=True)
        raise typer.Exit(1) from None
    typer.echo(f"Shadow image download complete: report={report_path}")


@app.command("shadow-generate-pending")
def shadow_generate_pending(
    image_manifest: Annotated[
        Path, typer.Option("--image-manifest", help="Verified image-pool JSONL manifest.")
    ],
    output_dir: Annotated[Path, typer.Option("--output-dir", help="New pending-record directory.")],
    image_ref_prefix: Annotated[
        str, typer.Option("--image-ref-prefix", help="Path prefix relative to Shadow image root.")
    ] = "image-pool-v1",
    seed: Annotated[int, typer.Option("--seed", help="Deterministic balance seed.")] = 236722600,
) -> None:
    """Generate 600 balanced candidates that remain pending independent review."""
    try:
        report_path = generate_pending_shadow_records(
            image_manifest,
            output_dir,
            image_ref_prefix=image_ref_prefix,
            seed=seed,
        )
    except (ShadowValidationError, OSError) as exc:
        typer.echo(f"Shadow pending generation failed: {exc}", err=True)
        raise typer.Exit(1) from None
    typer.echo(f"Shadow pending generation complete: report={report_path}")


def _jsonable(value: object) -> object:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(item) for item in value]
    return value
