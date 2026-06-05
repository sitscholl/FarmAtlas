from datetime import date as DateType
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


MetricType = Literal["days_since", "rain_since", "gdd_since"]
ScopeType = Literal["field", "planting", "section"]
RuleLogic = Literal["any", "all"]


class CropProtectionRuleProductRead(BaseModel):
    id: int
    product_name: str

    model_config = {"from_attributes": True}


class CropProtectionRuleScopeBase(BaseModel):
    scope_type: ScopeType
    scope_id: int

    @field_validator("scope_id")
    @classmethod
    def _validate_scope_id(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("scope_id must be greater than 0")
        return value


class CropProtectionRuleScopeRead(CropProtectionRuleScopeBase):
    id: int

    @model_validator(mode="before")
    @classmethod
    def from_model(cls, value):
        if hasattr(value, "field_id") and hasattr(value, "planting_id") and hasattr(value, "section_id"):
            if value.field_id is not None:
                return {"id": value.id, "scope_type": "field", "scope_id": value.field_id}
            if value.planting_id is not None:
                return {"id": value.id, "scope_type": "planting", "scope_id": value.planting_id}
            if value.section_id is not None:
                return {"id": value.id, "scope_type": "section", "scope_id": value.section_id}
        return value


class CropProtectionRuleMetricBase(BaseModel):
    metric_type: MetricType
    enabled: bool = True
    threshold: float
    warning_threshold: float | None = None
    metric_config: dict[str, Any] = Field(default_factory=dict)

    @field_validator("threshold")
    @classmethod
    def _validate_threshold(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("threshold must be greater than 0")
        return value

    @field_validator("warning_threshold")
    @classmethod
    def _validate_warning_threshold(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("warning_threshold must be greater than or equal to 0")
        return value


class CropProtectionRuleMetricRead(CropProtectionRuleMetricBase):
    id: int

    model_config = {"from_attributes": True}


class CropProtectionRulePayload(BaseModel):
    name: str
    enabled: bool = True
    season_start: DateType | None = None
    season_end: DateType | None = None
    logic: RuleLogic = "any"
    notes: str | None = None
    product_names: list[str]
    scopes: list[CropProtectionRuleScopeBase]
    metrics: list[CropProtectionRuleMetricBase]

    @field_validator("name")
    @classmethod
    def _validate_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized

    @field_validator("product_names")
    @classmethod
    def _validate_products(cls, value: list[str]) -> list[str]:
        normalized = sorted({item.strip() for item in value if item.strip()}, key=str.lower)
        if not normalized:
            raise ValueError("product_names must contain at least one product")
        return normalized

    @field_validator("scopes")
    @classmethod
    def _validate_scopes(cls, value: list[CropProtectionRuleScopeBase]) -> list[CropProtectionRuleScopeBase]:
        if not value:
            raise ValueError("scopes must contain at least one scope")
        return value

    @field_validator("metrics")
    @classmethod
    def _validate_metrics(cls, value: list[CropProtectionRuleMetricBase]) -> list[CropProtectionRuleMetricBase]:
        if not any(metric.enabled for metric in value):
            raise ValueError("metrics must contain at least one enabled metric")
        metric_types = [metric.metric_type for metric in value]
        if len(metric_types) != len(set(metric_types)):
            raise ValueError("metrics must not contain duplicate metric_type values")
        return value

    @model_validator(mode="after")
    def _validate_season_range(self):
        if self.season_start is not None and self.season_end is not None and self.season_end < self.season_start:
            raise ValueError("season_end must be greater than or equal to season_start")
        return self


class CropProtectionRuleCreate(CropProtectionRulePayload):
    pass


class CropProtectionRuleUpdate(CropProtectionRulePayload):
    pass


class CropProtectionRuleRead(BaseModel):
    id: int
    name: str
    enabled: bool
    season_start: DateType | None = None
    season_end: DateType | None = None
    logic: RuleLogic
    notes: str | None = None
    products: list[CropProtectionRuleProductRead]
    scopes: list[CropProtectionRuleScopeRead]
    metrics: list[CropProtectionRuleMetricRead]

    model_config = {"from_attributes": True}


class CropProtectionMetricEvaluationRead(BaseModel):
    metric_type: str
    value: float | int | None
    threshold: float
    warning_threshold: float | None = None
    status: str

    model_config = {"from_attributes": True}


class CropProtectionRuleEvaluationRead(BaseModel):
    rule_id: int
    rule_name: str
    section_id: int
    section_name: str
    field_id: int
    field_name: str
    status: str
    last_treatment_date: DateType | None = None
    last_treatment_product: str | None = None
    metrics: list[CropProtectionMetricEvaluationRead]

    model_config = {"from_attributes": True}


class CropProtectionFieldSummaryRead(BaseModel):
    field_id: int
    field_name: str
    status: str
    evaluation_count: int
    status_counts: dict[str, int]
    evaluations: list[CropProtectionRuleEvaluationRead]
