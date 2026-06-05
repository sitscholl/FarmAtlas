import datetime
from typing import Any

from sqlalchemy.orm import Session, selectinload

from .. import models


class CropProtectionRepository:
    def _query(self, session: Session):
        return session.query(models.CropProtectionRule).options(
            selectinload(models.CropProtectionRule.products),
            selectinload(models.CropProtectionRule.scopes),
            selectinload(models.CropProtectionRule.metrics),
        )

    def get_by_id(self, session: Session, rule_id: int) -> models.CropProtectionRule | None:
        return self._query(session).filter(models.CropProtectionRule.id == rule_id).one_or_none()

    def list_rules(self, session: Session, *, enabled: bool | None = None) -> list[models.CropProtectionRule]:
        query = self._query(session)
        if enabled is not None:
            query = query.filter(models.CropProtectionRule.enabled == enabled)
        return query.order_by(models.CropProtectionRule.name).all()

    def _validate_field_id(self, session: Session, field_id: int) -> None:
        if session.get(models.Field, field_id) is None:
            raise ValueError(f"No field with id {field_id} found")

    def _validate_planting_id(self, session: Session, planting_id: int) -> None:
        if session.get(models.Planting, planting_id) is None:
            raise ValueError(f"No planting with id {planting_id} found")

    def _validate_section_id(self, session: Session, section_id: int) -> None:
        if session.get(models.Section, section_id) is None:
            raise ValueError(f"No section with id {section_id} found")

    def _build_scope(self, session: Session, scope: dict[str, Any]) -> models.CropProtectionRuleScope:
        scope_type = str(scope["scope_type"]).strip().lower()
        scope_id = int(scope["scope_id"])
        if scope_type == "field":
            self._validate_field_id(session, scope_id)
            return models.CropProtectionRuleScope(field_id=scope_id)
        if scope_type == "planting":
            self._validate_planting_id(session, scope_id)
            return models.CropProtectionRuleScope(planting_id=scope_id)
        if scope_type == "section":
            self._validate_section_id(session, scope_id)
            return models.CropProtectionRuleScope(section_id=scope_id)
        raise ValueError("scope_type must be one of: field, planting, section")

    def _replace_children(
        self,
        session: Session,
        rule: models.CropProtectionRule,
        *,
        product_names: list[str],
        scopes: list[dict[str, Any]],
        metrics: list[dict[str, Any]],
    ) -> None:
        rule.products = [
            models.CropProtectionRuleProduct(product_name=product_name.strip())
            for product_name in sorted(set(product_names), key=str.lower)
            if product_name.strip()
        ]
        rule.scopes = [self._build_scope(session, scope) for scope in scopes]
        rule.metrics = [
            models.CropProtectionRuleMetric(
                metric_type=str(metric["metric_type"]).strip().lower(),
                enabled=bool(metric.get("enabled", True)),
                threshold=float(metric["threshold"]),
                warning_threshold=(
                    None
                    if metric.get("warning_threshold") is None
                    else float(metric["warning_threshold"])
                ),
                metric_config=dict(metric.get("metric_config") or {}),
            )
            for metric in metrics
        ]

    def create(
        self,
        session: Session,
        *,
        name: str,
        enabled: bool,
        season_start: datetime.date | None,
        season_end: datetime.date | None,
        logic: str,
        notes: str | None,
        product_names: list[str],
        scopes: list[dict[str, Any]],
        metrics: list[dict[str, Any]],
    ) -> models.CropProtectionRule:
        rule = models.CropProtectionRule(
            name=name.strip(),
            enabled=bool(enabled),
            season_start=season_start,
            season_end=season_end,
            logic=logic.strip().lower(),
            notes=None if notes is None or notes.strip() == "" else notes.strip(),
        )
        self._replace_children(session, rule, product_names=product_names, scopes=scopes, metrics=metrics)
        session.add(rule)
        session.flush()
        return self.get_by_id(session, rule.id) or rule

    def update(
        self,
        session: Session,
        rule_id: int,
        *,
        name: str,
        enabled: bool,
        season_start: datetime.date | None,
        season_end: datetime.date | None,
        logic: str,
        notes: str | None,
        product_names: list[str],
        scopes: list[dict[str, Any]],
        metrics: list[dict[str, Any]],
    ) -> models.CropProtectionRule:
        rule = self.get_by_id(session, rule_id)
        if rule is None:
            raise ValueError(f"Could not find any crop protection rule with id {rule_id}")

        rule.name = name.strip()
        rule.enabled = bool(enabled)
        rule.season_start = season_start
        rule.season_end = season_end
        rule.logic = logic.strip().lower()
        rule.notes = None if notes is None or notes.strip() == "" else notes.strip()
        rule.products.clear()
        rule.scopes.clear()
        rule.metrics.clear()
        session.flush()
        self._replace_children(session, rule, product_names=product_names, scopes=scopes, metrics=metrics)
        session.flush()
        return self.get_by_id(session, rule_id) or rule

    def delete(self, session: Session, rule_id: int) -> bool:
        rule = self.get_by_id(session, rule_id)
        if rule is None:
            return False
        session.delete(rule)
        return True

    def expand_rule_section_ids(self, session: Session, rule: models.CropProtectionRule) -> list[int]:
        section_ids: set[int] = set()
        for scope in rule.scopes:
            if scope.section_id is not None:
                section_ids.add(int(scope.section_id))
            elif scope.planting_id is not None:
                for section_id, in (
                    session.query(models.Section.id)
                    .filter(models.Section.planting_id == scope.planting_id)
                    .all()
                ):
                    section_ids.add(int(section_id))
            elif scope.field_id is not None:
                for section_id, in (
                    session.query(models.Section.id)
                    .join(models.Planting, models.Section.planting_id == models.Planting.id)
                    .filter(models.Planting.field_id == scope.field_id)
                    .all()
                ):
                    section_ids.add(int(section_id))
        return sorted(section_ids)

    def get_section_contexts(
        self,
        session: Session,
        section_ids: list[int],
    ) -> dict[int, models.Section]:
        if not section_ids:
            return {}
        sections = (
            session.query(models.Section)
            .options(
                selectinload(models.Section.planting).selectinload(models.Planting.field),
                selectinload(models.Section.planting).selectinload(models.Planting.variety),
            )
            .filter(models.Section.id.in_(section_ids))
            .all()
        )
        return {section.id: section for section in sections}

    def latest_matching_treatment(
        self,
        session: Session,
        *,
        section_id: int,
        product_names: list[str],
        start: datetime.date,
        end: datetime.date,
    ) -> models.TreatmentEvent | None:
        if not product_names:
            return None
        return (
            session.query(models.TreatmentEvent)
            .filter(
                models.TreatmentEvent.section_id == section_id,
                models.TreatmentEvent.product_name.in_(product_names),
                models.TreatmentEvent.date >= start,
                models.TreatmentEvent.date <= end,
            )
            .order_by(models.TreatmentEvent.date.desc(), models.TreatmentEvent.id.desc())
            .limit(1)
            .one_or_none()
        )
