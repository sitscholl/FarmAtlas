from pydantic import BaseModel, Field


class ProductionMetricDefinition(BaseModel):
    metric_code: str
    label: str
    unit: str | None = None


class FieldStatisticsMetric(BaseModel):
    value: float | None = None
    value_per_hectare: float | None = None
    source_scope: str | None = None
    source_mix: dict[str, int] = Field(default_factory=dict)
    sample_tree_count: int | None = None
    survey_count: int | None = None


class FieldStatisticsYearValue(BaseModel):
    season_year: int
    active: bool = True
    area: float = 0
    area_ha: float = 0
    section_count: int = 0
    tree_count: int | None = None
    metrics: dict[str, FieldStatisticsMetric] = Field(default_factory=dict)


class FieldStatisticsRow(BaseModel):
    field_id: int
    field_group: str
    field_name: str
    planting_id: int
    planting_name: str
    active: bool
    area: float
    area_ha: float
    section_count: int
    tree_count: int | None = None
    metrics: dict[str, FieldStatisticsMetric] = Field(default_factory=dict)
    history: list[FieldStatisticsYearValue] = Field(default_factory=list)


class FieldStatisticsSummary(BaseModel):
    label: str = "Summe"
    area: float
    area_ha: float
    section_count: int
    tree_count: int | None = None
    metrics: dict[str, FieldStatisticsMetric] = Field(default_factory=dict)
    history: list[FieldStatisticsYearValue] = Field(default_factory=list)


class FieldStatisticsResponse(BaseModel):
    season_year: int
    available_years: list[int] = Field(default_factory=list)
    history_years: list[int] = Field(default_factory=list)
    metrics: list[ProductionMetricDefinition] = Field(default_factory=list)
    rows: list[FieldStatisticsRow] = Field(default_factory=list)
    summary: FieldStatisticsSummary
