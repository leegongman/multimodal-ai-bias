"""Independent human review and adjudication boundary for Shadow Private records."""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from typing import Any

from multimodal_bias.exceptions import ShadowValidationError
from multimodal_bias.schemas import (
    ShadowAdjudicationDecision,
    ShadowAuditReport,
    ShadowEvidenceBasis,
    ShadowRecord,
    ShadowReviewApplicationResult,
    ShadowReviewDecision,
    ShadowReviewHistoryEntry,
    ShadowReviewReport,
    ShadowSubset,
)
from multimodal_bias.validation import audit_shadow_records, load_shadow_records

REVIEW_FIELDS = {
    "sample_id",
    "reviewer_id",
    "independent_label",
    "proposed_label",
    "decision",
    "evidence_basis",
    "evidence_note",
    "natural_language_ok",
    "protected_attribute_shortcut_absent",
    "content_safety_ok",
}
ADJUDICATION_FIELDS = {
    "sample_id",
    "adjudicator_id",
    "decision",
    "final_label",
    "final_subsets",
    "evidence_basis",
    "evidence_note",
    "natural_language_ok",
    "protected_attribute_shortcut_absent",
    "content_safety_ok",
}
REVIEW_DECISIONS = {"reviewed", "adjudication_required", "rejected"}
ADJUDICATION_DECISIONS = {"adjudicated", "rejected"}
EVIDENCE_BASES = {
    "insufficient_evidence",
    "stated_text_fact",
    "objective_visual_evidence",
    "valid_elimination",
}
SUBSET_EVIDENCE = {
    "ambiguous": {"insufficient_evidence"},
    "disambiguated_text": {"stated_text_fact"},
    "visual_grounded": {"objective_visual_evidence"},
    "elimination": {"valid_elimination"},
    "stereotype_trap": {"stated_text_fact"},
    "expression_trap": {"stated_text_fact"},
    "role_or_function": {"stated_text_fact"},
    "parsing_stress": {"stated_text_fact", "valid_elimination"},
}
SUPPORTED_SUBSETS = set(SUBSET_EVIDENCE)
QUALITY_FIELDS = (
    "natural_language_ok",
    "protected_attribute_shortcut_absent",
    "content_safety_ok",
)


def apply_shadow_reviews(
    dataset_path: Path,
    image_root: Path,
    decisions_path: Path,
    output_dir: Path,
    *,
    adjudications_path: Path | None = None,
) -> ShadowReviewApplicationResult:
    """Apply human decisions without mutating the pending corpus or hiding disputes."""
    _require_new_path(output_dir)
    records = load_shadow_records(dataset_path, image_root)
    raw_records = _load_jsonl_objects(dataset_path, "dataset")
    if len(records) != len(raw_records):
        raise ShadowValidationError("dataset record parsing changed row count")
    record_by_id = {record.sample_id: record for record in records}
    if len(record_by_id) != len(records):
        raise ShadowValidationError("duplicate sample_id in pending dataset")
    raw_by_id = {record.sample_id: raw for record, raw in zip(records, raw_records, strict=True)}
    decisions = _load_review_decisions(decisions_path)
    decision_by_id = _unique_by_sample_id(decisions, "review")
    for decision in decisions:
        record = record_by_id.get(decision.sample_id)
        if record is None:
            raise ShadowValidationError(
                f"unknown sample_id in review decisions: {decision.sample_id}"
            )
        _validate_review_binding(record, decision)

    adjudications = (
        _load_adjudications(adjudications_path) if adjudications_path is not None else ()
    )
    adjudication_by_id = _unique_by_sample_id(adjudications, "adjudication")
    for adjudication in adjudications:
        record = record_by_id.get(adjudication.sample_id)
        if record is None:
            raise ShadowValidationError(
                f"unknown sample_id in adjudications: {adjudication.sample_id}"
            )
        review = decision_by_id.get(adjudication.sample_id)
        if review is None or review.decision != "adjudication_required":
            raise ShadowValidationError(
                f"{adjudication.sample_id}: adjudication requires an adjudication_required review"
            )
        _validate_adjudication_binding(record, review, adjudication)

    reviewed_rows: list[dict[str, object]] = []
    reviewed_records: list[ShadowRecord] = []
    history_rows: list[dict[str, object]] = []
    dispute_rows: list[dict[str, object]] = []
    rejection_rows: list[dict[str, object]] = []
    reviewed_count = adjudicated_count = rejected_count = unresolved_disputes = 0

    for record in records:
        raw = raw_by_id[record.sample_id]
        review = decision_by_id.get(record.sample_id)
        if review is None:
            continue
        history_rows.append(_review_history_payload(record, raw, review))
        if review.decision == "reviewed":
            reviewed = _updated_record(record, status="reviewed", reviewer_id=review.reviewer_id)
            reviewed_records.append(reviewed)
            reviewed_rows.append(asdict(reviewed))
            reviewed_count += 1
            continue
        if review.decision == "rejected":
            rejection_rows.append(
                {"base_record": raw, "review_decision": asdict(review), "adjudication": None}
            )
            rejected_count += 1
            continue

        adjudication = adjudication_by_id.get(record.sample_id)
        dispute_payload: dict[str, object] = {
            "base_record": raw,
            "review_decision": asdict(review),
            "adjudication": asdict(adjudication) if adjudication else None,
        }
        dispute_rows.append(dispute_payload)
        if adjudication is None:
            unresolved_disputes += 1
            continue
        history_rows.append(_adjudication_history_payload(record, raw, adjudication))
        if adjudication.decision == "rejected":
            rejection_rows.append(dispute_payload)
            rejected_count += 1
            continue
        adjudicated = _updated_record(
            record,
            status="adjudicated",
            reviewer_id=adjudication.adjudicator_id,
            expected_label=adjudication.final_label,
            subsets=adjudication.final_subsets,
        )
        reviewed_records.append(adjudicated)
        reviewed_rows.append(asdict(adjudicated))
        adjudicated_count += 1

    coverage_report = audit_shadow_records(tuple(reviewed_records))
    missing_decision_count = len(records) - len(decisions)
    unresolved_count = missing_decision_count + unresolved_disputes
    violations: list[str] = []
    if len(records) != 600:
        violations.append("Story 4.3 review input must contain exactly 600 records")
    if len(decisions) != len(records):
        violations.append("all 600 input records require a terminal review decision")
    if unresolved_disputes:
        violations.append(f"{unresolved_disputes} disputes require adjudication")
    violations.extend(coverage_report.violations)
    report = ShadowReviewReport(
        input_record_count=len(records),
        decision_count=len(decisions),
        adjudication_count=len(adjudications),
        reviewed_count=reviewed_count,
        adjudicated_count=adjudicated_count,
        rejected_count=rejected_count,
        dispute_count=sum(d.decision == "adjudication_required" for d in decisions),
        missing_decision_count=missing_decision_count,
        retained_count=len(reviewed_records),
        unresolved_count=unresolved_count,
        violations=tuple(dict.fromkeys(violations)),
        promotion_ready=not violations,
        coverage_report=coverage_report,
    )
    return _publish_review_bundle(
        dataset_path,
        decisions_path,
        adjudications_path,
        output_dir,
        reviewed_rows,
        history_rows,
        dispute_rows,
        rejection_rows,
        report,
    )


def _load_review_decisions(path: Path) -> tuple[ShadowReviewDecision, ...]:
    rows = _load_jsonl_objects(path, "review decisions")
    decisions = []
    for line_number, raw in enumerate(rows, 1):
        _require_exact_fields(raw, REVIEW_FIELDS, "review", line_number)
        _require_non_empty_strings(raw, ("sample_id", "reviewer_id", "evidence_note"))
        _require_label(raw["independent_label"], "independent_label")
        _require_label(raw["proposed_label"], "proposed_label")
        if raw["decision"] not in REVIEW_DECISIONS:
            raise ShadowValidationError(f"review line {line_number}: invalid decision")
        _require_evidence_basis(raw["evidence_basis"], "review", line_number)
        _require_quality_booleans(raw, "review", line_number)
        decisions.append(ShadowReviewDecision(**raw))
    return tuple(decisions)


def _load_adjudications(path: Path) -> tuple[ShadowAdjudicationDecision, ...]:
    rows = _load_jsonl_objects(path, "adjudications")
    decisions = []
    for line_number, raw in enumerate(rows, 1):
        _require_exact_fields(raw, ADJUDICATION_FIELDS, "adjudication", line_number)
        _require_non_empty_strings(raw, ("sample_id", "adjudicator_id", "evidence_note"))
        _require_label(raw["final_label"], "final_label")
        if raw["decision"] not in ADJUDICATION_DECISIONS:
            raise ShadowValidationError(f"adjudication line {line_number}: invalid decision")
        _require_subsets(raw["final_subsets"], "adjudication", line_number)
        _require_evidence_basis(raw["evidence_basis"], "adjudication", line_number)
        _require_quality_booleans(raw, "adjudication", line_number)
        decisions.append(
            ShadowAdjudicationDecision(**{**raw, "final_subsets": tuple(raw["final_subsets"])})
        )
    return tuple(decisions)


def _validate_review_binding(record: ShadowRecord, decision: ShadowReviewDecision) -> None:
    if decision.reviewer_id == record.author_id:
        raise ShadowValidationError(
            f"{record.sample_id}: independent reviewer must differ from author"
        )
    if decision.proposed_label != record.expected_label:
        raise ShadowValidationError(f"{record.sample_id}: proposed_label does not match dataset")
    if decision.decision == "reviewed":
        if decision.independent_label != decision.proposed_label:
            raise ShadowValidationError(
                f"{record.sample_id}: reviewed decision requires matching independent_label"
            )
        if not _quality_checks_pass(decision):
            raise ShadowValidationError(
                f"{record.sample_id}: reviewed decision requires all quality checks"
            )
        _validate_evidence_binding(
            decision.independent_label,
            record.uncertainty_option_index,
            record.subsets,
            decision.evidence_basis,
            record.sample_id,
        )


def _validate_adjudication_binding(
    record: ShadowRecord,
    review: ShadowReviewDecision,
    adjudication: ShadowAdjudicationDecision,
) -> None:
    if adjudication.adjudicator_id == record.author_id:
        raise ShadowValidationError(f"{record.sample_id}: adjudicator must differ from author")
    if adjudication.adjudicator_id == review.reviewer_id:
        raise ShadowValidationError(f"{record.sample_id}: adjudicator must differ from reviewer")
    if adjudication.decision == "adjudicated":
        if not _quality_checks_pass(adjudication):
            raise ShadowValidationError(
                f"{record.sample_id}: adjudicated decision requires all quality checks"
            )
        _validate_evidence_binding(
            adjudication.final_label,
            record.uncertainty_option_index,
            adjudication.final_subsets,
            adjudication.evidence_basis,
            record.sample_id,
        )


def _validate_evidence_binding(
    label: int,
    uncertainty_position: int,
    subsets: tuple[ShadowSubset, ...],
    evidence_basis: ShadowEvidenceBasis,
    sample_id: str,
) -> None:
    if label == uncertainty_position:
        if evidence_basis != "insufficient_evidence" or "ambiguous" not in subsets:
            raise ShadowValidationError(
                f"{sample_id}: uncertainty label requires ambiguous/insufficient evidence"
            )
        return
    if evidence_basis == "insufficient_evidence" or "ambiguous" in subsets:
        raise ShadowValidationError(f"{sample_id}: resolvable label has inconsistent evidence")
    incompatible = [subset for subset in subsets if evidence_basis not in SUBSET_EVIDENCE[subset]]
    if incompatible:
        raise ShadowValidationError(
            f"{sample_id}: evidence_basis is incompatible with subsets {incompatible}"
        )


def _updated_record(
    record: ShadowRecord,
    *,
    status: str,
    reviewer_id: str,
    expected_label: int | None = None,
    subsets: tuple[ShadowSubset, ...] | None = None,
) -> ShadowRecord:
    payload = asdict(record)
    label = record.expected_label if expected_label is None else expected_label
    payload.update(
        {
            "expected_label": label,
            "expected_is_uncertainty": label == record.uncertainty_option_index,
            "subsets": record.subsets if subsets is None else subsets,
            "review_status": status,
            "reviewer_id": reviewer_id,
        }
    )
    return ShadowRecord(**payload)


def _review_history_payload(
    record: ShadowRecord, raw: dict[str, object], decision: ShadowReviewDecision
) -> dict[str, object]:
    after = record.expected_label if decision.decision == "reviewed" else None
    entry = ShadowReviewHistoryEntry(
        sample_id=record.sample_id,
        event_type="review",
        actor_id=decision.reviewer_id,
        decision=decision.decision,
        before_expected_label=record.expected_label,
        after_expected_label=after,
        before_subsets=record.subsets,
        after_subsets=record.subsets if after is not None else None,
        evidence_basis=decision.evidence_basis,
        evidence_note=decision.evidence_note,
        base_record_json=_canonical_json(raw),
        decision_json=_canonical_json(asdict(decision)),
    )
    return _history_payload(entry)


def _adjudication_history_payload(
    record: ShadowRecord, raw: dict[str, object], decision: ShadowAdjudicationDecision
) -> dict[str, object]:
    after = decision.final_label if decision.decision == "adjudicated" else None
    entry = ShadowReviewHistoryEntry(
        sample_id=record.sample_id,
        event_type="adjudication",
        actor_id=decision.adjudicator_id,
        decision=decision.decision,
        before_expected_label=record.expected_label,
        after_expected_label=after,
        before_subsets=record.subsets,
        after_subsets=decision.final_subsets if after is not None else None,
        evidence_basis=decision.evidence_basis,
        evidence_note=decision.evidence_note,
        base_record_json=_canonical_json(raw),
        decision_json=_canonical_json(asdict(decision)),
    )
    return _history_payload(entry)


def _history_payload(entry: ShadowReviewHistoryEntry) -> dict[str, object]:
    payload = asdict(entry)
    payload["base_record"] = json.loads(str(payload.pop("base_record_json")))
    payload["decision_payload"] = json.loads(str(payload.pop("decision_json")))
    return payload


def _publish_review_bundle(
    dataset_path: Path,
    decisions_path: Path,
    adjudications_path: Path | None,
    output_dir: Path,
    reviewed_rows: list[dict[str, object]],
    history_rows: list[dict[str, object]],
    dispute_rows: list[dict[str, object]],
    rejection_rows: list[dict[str, object]],
    report: ShadowReviewReport,
) -> ShadowReviewApplicationResult:
    staging = output_dir.with_name(output_dir.name + ".partial")
    _require_new_path(staging)
    try:
        staging.mkdir(parents=True)
        paths = {
            "reviewed": staging / "reviewed.jsonl",
            "history": staging / "review-history.jsonl",
            "disputes": staging / "disputes.jsonl",
            "rejections": staging / "rejections.jsonl",
            "report": staging / "report.json",
        }
        _write_jsonl(paths["reviewed"], reviewed_rows)
        _write_jsonl(paths["history"], history_rows)
        _write_jsonl(paths["disputes"], dispute_rows)
        _write_jsonl(paths["rejections"], rejection_rows)
        _write_json(paths["report"], _report_payload(report))
        manifest = {
            "schema_version": "shadow-review-application-v1",
            "base_dataset_sha256": _file_sha256(dataset_path),
            "review_decisions_sha256": _file_sha256(decisions_path),
            "adjudications_sha256": (
                _file_sha256(adjudications_path) if adjudications_path is not None else None
            ),
            "output_sha256": {
                f"{name}.json" if name == "report" else paths[name].name: _file_sha256(path)
                for name, path in paths.items()
            },
            "promotion_ready": report.promotion_ready,
        }
        manifest_path = staging / "manifest.json"
        _write_json(manifest_path, manifest)
        staging.rename(output_dir)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    return ShadowReviewApplicationResult(
        output_dir=output_dir,
        reviewed_path=output_dir / "reviewed.jsonl",
        history_path=output_dir / "review-history.jsonl",
        disputes_path=output_dir / "disputes.jsonl",
        rejections_path=output_dir / "rejections.jsonl",
        report_path=output_dir / "report.json",
        manifest_path=output_dir / "manifest.json",
        report=report,
    )


def _report_payload(report: ShadowReviewReport) -> dict[str, object]:
    return {
        "input_record_count": report.input_record_count,
        "decision_count": report.decision_count,
        "adjudication_count": report.adjudication_count,
        "reviewed_count": report.reviewed_count,
        "adjudicated_count": report.adjudicated_count,
        "rejected_count": report.rejected_count,
        "dispute_count": report.dispute_count,
        "missing_decision_count": report.missing_decision_count,
        "retained_count": report.retained_count,
        "unresolved_count": report.unresolved_count,
        "violations": list(report.violations),
        "promotion_ready": report.promotion_ready,
        "coverage_report": _audit_payload(report.coverage_report),
    }


def _audit_payload(report: ShadowAuditReport) -> dict[str, object]:
    return {
        "record_count": report.record_count,
        "reviewed_count": report.reviewed_count,
        "rejected_count": report.rejected_count,
        "split_counts": dict(report.split_counts),
        "subset_counts": dict(report.subset_counts),
        "uncertainty_position_counts": dict(report.uncertainty_position_counts),
        "expected_label_counts": dict(report.expected_label_counts),
        "ambiguous_count": report.ambiguous_count,
        "resolvable_count": report.resolvable_count,
        "violations": list(report.violations),
        "promotion_ready": report.promotion_ready,
    }


def _load_jsonl_objects(path: Path, label: str) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ShadowValidationError(f"{label} file does not exist: {path}")
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ShadowValidationError(f"{label} must be UTF-8") from exc
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            raise ShadowValidationError(f"{label} line {line_number}: blank line")
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ShadowValidationError(f"{label} line {line_number}: invalid JSON") from exc
        if not isinstance(row, dict):
            raise ShadowValidationError(f"{label} line {line_number}: must be an object")
        rows.append(row)
    return rows


def _unique_by_sample_id(values: tuple[Any, ...], label: str) -> dict[str, Any]:
    result = {}
    for value in values:
        if value.sample_id in result:
            raise ShadowValidationError(
                f"duplicate sample_id in {label} decisions: {value.sample_id}"
            )
        result[value.sample_id] = value
    return result


def _require_exact_fields(
    raw: dict[str, Any], expected: set[str], label: str, line_number: int
) -> None:
    missing = expected - raw.keys()
    unknown = raw.keys() - expected
    if missing:
        raise ShadowValidationError(
            f"{label} line {line_number}: missing fields: {', '.join(sorted(missing))}"
        )
    if unknown:
        raise ShadowValidationError(
            f"{label} line {line_number}: unknown fields: {', '.join(sorted(unknown))}"
        )


def _require_non_empty_strings(raw: dict[str, Any], fields: tuple[str, ...]) -> None:
    for field in fields:
        if not isinstance(raw[field], str) or not raw[field].strip():
            raise ShadowValidationError(f"{field} must be a non-empty string")


def _require_label(value: object, field: str) -> None:
    if type(value) is not int or value not in range(3):
        raise ShadowValidationError(f"{field} must be 0, 1, or 2")


def _require_evidence_basis(value: object, label: str, line_number: int) -> None:
    if value not in EVIDENCE_BASES:
        raise ShadowValidationError(f"{label} line {line_number}: invalid evidence_basis")


def _require_quality_booleans(raw: dict[str, Any], label: str, line_number: int) -> None:
    if any(type(raw[field]) is not bool for field in QUALITY_FIELDS):
        raise ShadowValidationError(f"{label} line {line_number}: quality checks must be boolean")


def _require_subsets(value: object, label: str, line_number: int) -> None:
    if (
        not isinstance(value, list)
        or not value
        or len(value) != len(set(value))
        or any(subset not in SUPPORTED_SUBSETS for subset in value)
    ):
        raise ShadowValidationError(f"{label} line {line_number}: invalid final_subsets")


def _quality_checks_pass(value: ShadowReviewDecision | ShadowAdjudicationDecision) -> bool:
    return all(getattr(value, field) is True for field in QUALITY_FIELDS)


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("".join(_canonical_json(row) + "\n" for row in rows), encoding="utf-8")


def _write_json(path: Path, value: object) -> None:
    path.write_text(_canonical_json(value) + "\n", encoding="utf-8")


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _require_new_path(path: Path) -> None:
    if path.exists():
        raise ShadowValidationError(f"refusing to overwrite existing path: {path}")
