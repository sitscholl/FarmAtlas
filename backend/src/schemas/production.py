from datetime import date

from pydantic import BaseModel, Field


class ProductionMetricDefinition(BaseModel):
    metric_code: str
    label: str
    unit: str | None = None


class ProductionYearValue(BaseModel):
    season_year: int
    value: float | None = None
    source_scope: str | None = None
    source_mix: dict[str, int] = Field(default_factory=dict)


class ProductionComparisonMetric(ProductionMetricDefinition):
    current_value: float | None = None
    previous_value: float | None = None
    percent_change: float | None = None
    current_source_scope: str | None = None
    current_source_mix: dict[str, int] = Field(default_factory=dict)
    history: list[ProductionYearValue] = Field(default_factory=list)


class PlantingYearComparisonRow(BaseModel):
    field_id: int
    field_group: str
    field_name: str
    planting_id: int
    variety: str
    valid_from: date
    valid_to: date | None = None
    active: bool
    section_count: int
    area: float
    tree_count: int | None = None
    metrics: list[ProductionComparisonMetric] = Field(default_factory=list)


class PlantingYearComparisonResponse(BaseModel):
    season_year: int
    previous_year: int
    history_years: list[int]
    metrics: list[ProductionMetricDefinition] = Field(default_factory=list)
    rows: list[PlantingYearComparisonRow] = Field(default_factory=list)
