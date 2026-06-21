import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from ..schemas import (
    CropProtectionFieldSummaryRead,
    CropProtectionRuleCreate,
    CropProtectionRuleEvaluationRead,
    CropProtectionRuleRead,
    CropProtectionRuleUpdate,
)
from .utils import raise_write_http_error, runtime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/crop-protection", tags=["crop-protection"])

_STATUS_RANK = {
    "due": 4,
    "soon": 3,
    "missing": 2,
    "ok": 1,
}


def _rule_payload(rule: CropProtectionRuleCreate | CropProtectionRuleUpdate) -> dict:
    data = rule.model_dump()
    data["scopes"] = [scope.model_dump() for scope in rule.scopes]
    data["metrics"] = [metric.model_dump() for metric in rule.metrics]
    return data


@router.get("/rules", response_model=list[CropProtectionRuleRead])
async def list_crop_protection_rules(enabled: bool | None = None):
    with runtime.db.session_scope() as session:
        rules = runtime.db.crop_protection.list_rules(session, enabled=enabled)
    return [CropProtectionRuleRead.model_validate(rule) for rule in rules]


@router.post("/rules", response_model=CropProtectionRuleRead, status_code=status.HTTP_201_CREATED)
async def create_crop_protection_rule(rule: CropProtectionRuleCreate):
    try:
        created = runtime.db.crop_protection_service.create_rule(**_rule_payload(rule))
        return CropProtectionRuleRead.model_validate(created)
    except Exception as exc:
        logger.exception("Creating crop protection rule failed: %s", exc)
        raise_write_http_error(exc, not_found_prefixes=("No field with id", "No planting with id", "No section with id"))


@router.get("/rules/{rule_id}", response_model=CropProtectionRuleRead)
async def get_crop_protection_rule(rule_id: int):
    with runtime.db.session_scope() as session:
        rule = runtime.db.crop_protection.get_by_id(session, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail=f"Could not find any crop protection rule with id {rule_id}")
    return CropProtectionRuleRead.model_validate(rule)


@router.put("/rules/{rule_id}", response_model=CropProtectionRuleRead)
async def update_crop_protection_rule(rule_id: int, rule: CropProtectionRuleUpdate):
    try:
        updated = runtime.db.crop_protection_service.update_rule(rule_id, **_rule_payload(rule))
        return CropProtectionRuleRead.model_validate(updated)
    except Exception as exc:
        logger.exception("Updating crop protection rule %s failed: %s", rule_id, exc)
        raise_write_http_error(
            exc,
            not_found_prefixes=(
                "No field with id",
                "No planting with id",
                "No section with id",
                "Could not find any crop protection rule with id",
            ),
        )


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_crop_protection_rule(rule_id: int):
    deleted = runtime.db.crop_protection_service.delete_rule(rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Could not find any crop protection rule with id {rule_id}")


@router.get("/evaluations", response_model=list[CropProtectionRuleEvaluationRead])
async def evaluate_crop_protection_rules(
    rule_id: int | None = None,
    season_year: int | None = None,
    as_of: datetime | None = None,
    include_disabled: bool = False,
):
    try:
        evaluations = runtime.db.crop_protection_service.evaluate_rules(
            rule_id=rule_id,
            season_year=season_year,
            as_of=as_of,
            include_disabled=include_disabled,
        )
        return [CropProtectionRuleEvaluationRead.model_validate(evaluation) for evaluation in evaluations]
    except Exception as exc:
        logger.exception("Evaluating crop protection rules failed: %s", exc)
        raise_write_http_error(exc, not_found_prefixes=("Could not find any crop protection rule with id",))


@router.get("/field-summaries", response_model=list[CropProtectionFieldSummaryRead])
async def summarize_crop_protection_by_field(
    season_year: int | None = None,
    as_of: datetime | None = None,
    include_disabled: bool = False,
):
    try:
        evaluations = runtime.db.crop_protection_service.evaluate_rules(
            season_year=season_year,
            as_of=as_of,
            include_disabled=include_disabled,
        )
    except Exception as exc:
        logger.exception("Summarizing crop protection by field failed: %s", exc)
        raise_write_http_error(exc)

    groups: dict[int, list] = {}
    for evaluation in evaluations:
        groups.setdefault(evaluation.field_id, []).append(evaluation)

    summaries: list[CropProtectionFieldSummaryRead] = []
    for field_id, field_evaluations in groups.items():
        sorted_evaluations = sorted(
            field_evaluations,
            key=lambda evaluation: _STATUS_RANK.get(evaluation.status, 0),
            reverse=True,
        )
        status_counts: dict[str, int] = {}
        for evaluation in sorted_evaluations:
            status_counts[evaluation.status] = status_counts.get(evaluation.status, 0) + 1
        worst_status = sorted_evaluations[0].status if sorted_evaluations else "missing"
        weather_updated_at = min(
            (
                evaluation.weather_updated_at
                for evaluation in sorted_evaluations
                if evaluation.weather_updated_at is not None
            ),
            default=None,
        )
        warnings = [
            warning
            for evaluation in sorted_evaluations
            for warning in evaluation.warnings
        ]

        summaries.append(
            CropProtectionFieldSummaryRead(
                field_id=field_id,
                field_name=sorted_evaluations[0].field_name,
                status=worst_status,
                evaluation_count=len(sorted_evaluations),
                status_counts=status_counts,
                weather_updated_at=weather_updated_at,
                warnings=warnings,
                evaluations=[
                    CropProtectionRuleEvaluationRead.model_validate(evaluation)
                    for evaluation in sorted_evaluations
                ],
            )
        )

    return sorted(
        summaries,
        key=lambda summary: (_STATUS_RANK.get(summary.status, 0), summary.field_name.lower()),
        reverse=True,
    )


@router.get("/rules/{rule_id}/evaluations", response_model=list[CropProtectionRuleEvaluationRead])
async def evaluate_crop_protection_rule(
    rule_id: int,
    season_year: int | None = None,
    as_of: datetime | None = None,
    include_disabled: bool = False,
):
    return await evaluate_crop_protection_rules(
        rule_id=rule_id,
        season_year=season_year,
        as_of=as_of,
        include_disabled=include_disabled,
    )
