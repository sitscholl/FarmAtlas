from datetime import date as DateType, datetime

from pydantic import BaseModel, field_validator

from .base import ORMModel


class TreatmentImportRead(ORMModel):
    id: int
    source: str
    season_year: int
    imported_at: datetime
    row_count: int
    unresolved_count: int


class TreatmentEventRead(ORMModel):
    id: int
    source: str
    season_year: int
    date: DateType
    external_section_name: str
    section_id: int | None = None
    product_name: str
    reason: str | None = None
    dose_per_hl: float | None = None
    hl: float | None = None
    cost: float | None = None
    row_hash: str
    resolution_status: str


class TreatmentSectionAliasBase(BaseModel):
    source: str = "legal_export"
    external_section_name: str
    section_id: int

    @field_validator("source", "external_section_name")
    @classmethod
    def _normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized


class TreatmentSectionAliasCreate(TreatmentSectionAliasBase):
    pass


class TreatmentSectionAliasUpdate(TreatmentSectionAliasBase):
    pass


class TreatmentSectionAliasRead(TreatmentSectionAliasBase, ORMModel):
    id: int


class TreatmentCsvImportResponse(BaseModel):
    import_summary: TreatmentImportRead
    unresolved_external_section_names: list[str]
