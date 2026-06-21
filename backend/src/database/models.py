import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import declarative_base, relationship

from ..domain.phenology import get_phenological_stage

Base = declarative_base()


class ValidityRangeMixin:
    valid_from = Column(Date, nullable=False)
    valid_to = Column(Date, nullable=True)

    @property
    def active(self) -> bool:
        today = datetime.date.today()
        return self.valid_from <= today and (self.valid_to is None or self.valid_to >= today)


class Field(Base):
    __tablename__ = "fields"
    __table_args__ = (
        UniqueConstraint("group", "name", name="uq_fields_group_name"),
    )

    id = Column(Integer, primary_key=True)
    group = Column(String, nullable=False)
    name = Column(String, nullable=False)

    reference_provider = Column(String, nullable=False)
    reference_station = Column(String, nullable=False)

    elevation = Column(Float, nullable=False)
    soil_type = Column(String, nullable=True)
    soil_weight = Column(String, nullable=True)
    humus_pct = Column(Float, nullable=True)
    effective_root_depth_cm = Column(Float, nullable=True)
    p_allowable = Column(Float, nullable=True)  # Fraction depleted before stress.
    drip_distance = Column(Float, nullable=True)  # Distance between drip holes in tube.
    drip_discharge = Column(Float, nullable=True)  # Liters per hour per drip hole.
    tree_strip_width = Column(Float, nullable=True)  # Width irrigated by the drip line.
    valve_open = Column(Boolean, default=True, nullable=False)

    plantings = relationship(
        "Planting",
        back_populates="field",
        cascade="all, delete-orphan",
        order_by="Planting.valid_from",
    )
    cadastral_parcels = relationship(
        "CadastralParcel",
        back_populates="field",
        cascade="all, delete-orphan",
    )
    irrigation_events = relationship(
        "Irrigation",
        back_populates="field",
        cascade="all, delete-orphan",
    )
    fruit_count_surveys = relationship(
        "FruitCountSurvey",
        back_populates="field",
        cascade="all, delete-orphan",
    )
    yearly_stats = relationship(
        "YearlyStats",
        back_populates="field",
        cascade="all, delete-orphan",
    )

    @property
    def sections(self) -> list["Section"]:
        return [section for planting in self.plantings for section in planting.sections]

    @property
    def area(self) -> float:
        return sum(float(section.area) for section in self.sections)

    @property
    def tree_count(self) -> int | None:
        counts = [int(section.tree_count) for section in self.sections if section.tree_count is not None]
        return sum(counts) if counts else None

    @property
    def running_metre(self) -> int | None:
        counts = [int(section.running_metre) for section in self.sections if section.running_metre is not None]
        return sum(counts) if counts else None


class Planting(Base, ValidityRangeMixin):
    __tablename__ = "plantings"
    __table_args__ = (
        CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_plantings_valid_range",
        ),
        Index(
            "uq_plantings_field_variety_valid_from",
            "field_id",
            "variety_id",
            "valid_from",
            unique=True,
        ),
    )

    id = Column(Integer, primary_key=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False)
    variety_id = Column(Integer, ForeignKey("varieties.id"), nullable=False)

    field = relationship("Field", back_populates="plantings")
    variety = relationship("Variety", back_populates="plantings")
    sections = relationship(
        "Section",
        back_populates="planting",
        cascade="all, delete-orphan",
        order_by="Section.valid_from",
    )
    fruit_count_surveys = relationship(
        "FruitCountSurvey",
        back_populates="planting",
        cascade="all, delete-orphan",
    )
    yearly_stats = relationship(
        "YearlyStats",
        back_populates="planting",
        cascade="all, delete-orphan",
    )

    @property
    def area(self) -> float:
        return sum(float(section.area) for section in self.sections)

    @property
    def tree_count(self) -> int | None:
        counts = [int(section.tree_count) for section in self.sections if section.tree_count is not None]
        return sum(counts) if counts else None

    @property
    def running_metre(self) -> int | None:
        counts = [int(section.running_metre) for section in self.sections if section.running_metre is not None]
        return sum(counts) if counts else None


class Section(Base, ValidityRangeMixin):
    __tablename__ = "sections"
    __table_args__ = (
        CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_sections_valid_range",
        ),
        Index(
            "uq_sections_planting_valid_from",
            "planting_id",
            "name",
            unique=True,
        ),
    )

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    planting_id = Column(Integer, ForeignKey("plantings.id"), nullable=False)

    planting_year = Column(Integer, nullable=False)
    area = Column(Float, nullable=False)  # In m^2.
    tree_count = Column(Integer, nullable=True)
    tree_height = Column(Float, nullable=True)
    row_distance = Column(Float, nullable=True)
    tree_distance = Column(Float, nullable=True)
    running_metre = Column(Float, nullable=True)
    herbicide_free = Column(Boolean, nullable=True)

    planting = relationship("Planting", back_populates="sections")
    phenology_events = relationship(
        "SectionPhenologyEvent",
        back_populates="section",
        cascade="all, delete-orphan",
        order_by="SectionPhenologyEvent.date",
    )
    treatment_events = relationship(
        "TreatmentEvent",
        back_populates="section",
        cascade="all, delete-orphan",
    )
    treatment_aliases = relationship(
        "TreatmentSectionAlias",
        back_populates="section",
        cascade="all, delete-orphan",
    )
    crop_protection_scopes = relationship(
        "CropProtectionRuleScope",
        back_populates="section",
    )
    fruit_count_surveys = relationship(
        "FruitCountSurvey",
        back_populates="section",
        cascade="all, delete-orphan",
    )
    yearly_stats = relationship(
        "YearlyStats",
        back_populates="section",
        cascade="all, delete-orphan",
    )

    @property
    def field(self) -> Field | None:
        return self.planting.field if self.planting is not None else None

    @property
    def variety(self) -> "Variety | None":
        return self.planting.variety if self.planting is not None else None

    @property
    def current_phenology_event(self) -> "SectionPhenologyEvent | None":
        today = datetime.date.today()
        active_events = [event for event in self.phenology_events if event.date <= today]
        if not active_events:
            return None
        return max(active_events, key=lambda event: event.date)

    @property
    def current_phenology(self) -> str | None:
        current_event = self.current_phenology_event
        if current_event is None:
            return None
        stage = get_phenological_stage(current_event.stage_code)
        return current_event.stage_code if stage is None else stage.label


class CadastralParcel(Base):
    __tablename__ = "field_cadastral_parcels"
    __table_args__ = (
        UniqueConstraint(
            "field_id",
            "municipality_id",
            "parcel_id",
            name="uq_field_cadastral_parcels_identity",
        ),
        CheckConstraint("area >= 0", name="ck_field_cadastral_parcels_area_non_negative"),
    )

    id = Column(Integer, primary_key=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False)
    parcel_id = Column(String, nullable=False)
    municipality_id = Column(String, nullable=False)
    area = Column(Float, nullable=False)

    field = relationship("Field", back_populates="cadastral_parcels")


class Variety(Base):
    __tablename__ = "varieties"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    group = Column(String, nullable=False)

    nr_per_kg = Column(Float, nullable=True)
    kg_per_box = Column(Float, nullable=True)
    slope = Column(Float, nullable=True)
    intercept = Column(Float, nullable=True)
    specific_weight = Column(Float, nullable=True)  # g/cm^3

    plantings = relationship("Planting", back_populates="variety")
    nutrient_requirements = relationship(
        "NutrientRequirement",
        back_populates="variety",
        cascade="all, delete-orphan",
    )


class NutrientRequirement(Base):
    __tablename__ = "nutrients"
    __table_args__ = (
        Index(
            "uq_nutrients_global_default",
            "nutrient_code",
            unique=True,
            sqlite_where=text("variety_id IS NULL"),
        ),
        Index(
            "uq_nutrients_variety_override",
            "nutrient_code",
            "variety_id",
            unique=True,
            sqlite_where=text("variety_id IS NOT NULL"),
        ),
    )

    id = Column(Integer, primary_key=True)
    variety_id = Column(Integer, ForeignKey("varieties.id"), nullable=True, default=None)
    nutrient_code = Column(String, nullable=False)
    requirement_per_kg_min = Column(Float, nullable=False)
    requirement_per_kg_mean = Column(Float, nullable=False)
    requirement_per_kg_max = Column(Float, nullable=False)

    variety = relationship("Variety", back_populates="nutrient_requirements")


class Irrigation(Base):
    __tablename__ = "irrigation_events"
    __table_args__ = (
        UniqueConstraint("field_id", "date", name="uq_irrigation_field_date"),
    )

    id = Column(Integer, primary_key=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False)
    date = Column(Date, nullable=False)
    method = Column(String, nullable=False)
    duration = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)  # Amount of irrigation water in mm.

    field = relationship("Field", back_populates="irrigation_events")

    def __repr__(self) -> str:
        return f"Irrigation(id={self.id!r}, field_id={self.field_id!r}, date={self.date!r})"


class StationWeatherHourly(Base):
    __tablename__ = "station_weather_hourly"
    __table_args__ = (
        UniqueConstraint(
            "source_provider",
            "source_station",
            "timestamp",
            name="uq_station_weather_hourly_station_timestamp",
        ),
    )

    source_provider = Column(String, primary_key=True)
    source_station = Column(String, primary_key=True)
    timestamp = Column(DateTime(timezone=True), primary_key=True)
    precipitation = Column(Float, nullable=True)
    tair_2m = Column(Float, nullable=True)
    relative_humidity = Column(Float, nullable=True)
    wind_speed = Column(Float, nullable=True)
    wind_gust = Column(Float, nullable=True)
    air_pressure = Column(Float, nullable=True)
    sun_duration = Column(Float, nullable=True)
    solar_radiation = Column(Float, nullable=True)
    value_type = Column(String, nullable=False, default="observed")
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.datetime.now)


class StationWeatherMetadata(Base):
    __tablename__ = "station_weather_metadata"

    source_provider = Column(String, primary_key=True)
    source_station = Column(String, primary_key=True)
    longitude = Column(Float, nullable=False)
    latitude = Column(Float, nullable=False)
    crs = Column(Integer, nullable=False, default=4326)
    elevation = Column(Float, nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.datetime.now)


class TreatmentImport(Base):
    __tablename__ = "treatment_imports"
    __table_args__ = (
        UniqueConstraint("source", "season_year", name="uq_treatment_imports_source_season"),
    )

    id = Column(Integer, primary_key=True)
    source = Column(String, nullable=False)
    season_year = Column(Integer, nullable=False)
    imported_at = Column(DateTime(timezone=True), nullable=False, default=datetime.datetime.now)
    row_count = Column(Integer, nullable=False)
    unresolved_count = Column(Integer, nullable=False)


class TreatmentSectionAlias(Base):
    __tablename__ = "treatment_section_aliases"
    __table_args__ = (
        UniqueConstraint("source", "external_section_name", name="uq_treatment_section_aliases_source_name"),
    )

    id = Column(Integer, primary_key=True)
    source = Column(String, nullable=False)
    external_section_name = Column(String, nullable=False)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=False)

    section = relationship("Section", back_populates="treatment_aliases")


class TreatmentEvent(Base):
    __tablename__ = "treatment_events"
    __table_args__ = (
        UniqueConstraint("source", "season_year", "row_hash", name="uq_treatment_events_source_season_hash"),
        Index("ix_treatment_events_section_date", "section_id", "date"),
        Index("ix_treatment_events_product", "product_name"),
    )

    id = Column(Integer, primary_key=True)
    source = Column(String, nullable=False)
    season_year = Column(Integer, nullable=False)
    date = Column(Date, nullable=False)
    external_section_name = Column(String, nullable=False)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=True)
    product_name = Column(String, nullable=False)
    reason = Column(String, nullable=True)
    dose_per_hl = Column(Float, nullable=True)
    hl = Column(Float, nullable=True)
    cost = Column(Float, nullable=True)
    row_hash = Column(String, nullable=False)
    resolution_status = Column(String, nullable=False)

    section = relationship("Section", back_populates="treatment_events")


class CropProtectionRule(Base):
    __tablename__ = "crop_protection_rules"
    __table_args__ = (
        CheckConstraint("logic IN ('any', 'all')", name="ck_crop_protection_rules_logic"),
    )

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    season_start = Column(Date, nullable=True)
    season_end = Column(Date, nullable=True)
    logic = Column(String, nullable=False, default="any")
    notes = Column(String, nullable=True)

    products = relationship(
        "CropProtectionRuleProduct",
        back_populates="rule",
        cascade="all, delete-orphan",
        order_by="CropProtectionRuleProduct.product_name",
    )
    scopes = relationship(
        "CropProtectionRuleScope",
        back_populates="rule",
        cascade="all, delete-orphan",
    )
    metrics = relationship(
        "CropProtectionRuleMetric",
        back_populates="rule",
        cascade="all, delete-orphan",
        order_by="CropProtectionRuleMetric.metric_type",
    )


class CropProtectionRuleProduct(Base):
    __tablename__ = "crop_protection_rule_products"
    __table_args__ = (
        UniqueConstraint("rule_id", "product_name", name="uq_crop_protection_rule_products_rule_product"),
    )

    id = Column(Integer, primary_key=True)
    rule_id = Column(Integer, ForeignKey("crop_protection_rules.id"), nullable=False)
    product_name = Column(String, nullable=False)

    rule = relationship("CropProtectionRule", back_populates="products")


class CropProtectionRuleScope(Base):
    __tablename__ = "crop_protection_rule_scopes"
    __table_args__ = (
        CheckConstraint(
            "(field_id IS NOT NULL) + (planting_id IS NOT NULL) + (section_id IS NOT NULL) = 1",
            name="ck_crop_protection_rule_scopes_one_scope",
        ),
        UniqueConstraint(
            "rule_id",
            "field_id",
            "planting_id",
            "section_id",
            name="uq_crop_protection_rule_scopes_rule_scope",
        ),
    )

    id = Column(Integer, primary_key=True)
    rule_id = Column(Integer, ForeignKey("crop_protection_rules.id"), nullable=False)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=True)
    planting_id = Column(Integer, ForeignKey("plantings.id"), nullable=True)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=True)

    rule = relationship("CropProtectionRule", back_populates="scopes")
    field = relationship("Field")
    planting = relationship("Planting")
    section = relationship("Section", back_populates="crop_protection_scopes")


class CropProtectionRuleMetric(Base):
    __tablename__ = "crop_protection_rule_metrics"
    __table_args__ = (
        CheckConstraint(
            "metric_type IN ('days_since', 'rain_since', 'gdd_since')",
            name="ck_crop_protection_rule_metrics_type",
        ),
        UniqueConstraint("rule_id", "metric_type", name="uq_crop_protection_rule_metrics_rule_type"),
    )

    id = Column(Integer, primary_key=True)
    rule_id = Column(Integer, ForeignKey("crop_protection_rules.id"), nullable=False)
    metric_type = Column(String, nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    threshold = Column(Float, nullable=False)
    warning_threshold = Column(Float, nullable=True)
    metric_config = Column(JSON, nullable=True)

    rule = relationship("CropProtectionRule", back_populates="metrics")


class SectionPhenologyEvent(Base):
    __tablename__ = "section_phenology_events"
    __table_args__ = (
        UniqueConstraint("section_id", "date", name="uq_section_phenology_events_section_date"),
        UniqueConstraint(
            "section_id",
            "stage_code",
            "year",
            name="uq_section_phenology_events_section_stage_year",
        ),
    )

    id = Column(Integer, primary_key=True)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=False)
    stage_code = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    year = Column(Integer, nullable=False)

    section = relationship("Section", back_populates="phenology_events")


class FruitCountSurvey(Base):
    __tablename__ = "fruit_count_surveys"
    __table_args__ = (
        CheckConstraint(
            "(field_id IS NOT NULL) + (planting_id IS NOT NULL) + (section_id IS NOT NULL) = 1",
            name="ck_fruit_count_surveys_one_scope",
        ),
        CheckConstraint("season_year >= 1900", name="ck_fruit_count_surveys_season_year"),
        Index("ix_fruit_count_surveys_field_year_timing", "field_id", "season_year", "timing_code"),
        Index("ix_fruit_count_surveys_planting_year_timing", "planting_id", "season_year", "timing_code"),
        Index("ix_fruit_count_surveys_section_year_timing", "section_id", "season_year", "timing_code"),
    )

    id = Column(Integer, primary_key=True)
    season_year = Column(Integer, nullable=False)
    date = Column(Date, nullable=False)
    timing_code = Column(String, nullable=False)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=True)
    planting_id = Column(Integer, ForeignKey("plantings.id"), nullable=True)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=True)
    method = Column(String, nullable=True)
    observer = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    include_in_aggregation = Column(Boolean, nullable=False, default=True)
    quality_flag = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.datetime.now)

    field = relationship("Field", back_populates="fruit_count_surveys")
    planting = relationship("Planting", back_populates="fruit_count_surveys")
    section = relationship("Section", back_populates="fruit_count_surveys")
    samples = relationship(
        "FruitCountSample",
        back_populates="survey",
        cascade="all, delete-orphan",
        order_by="FruitCountSample.id",
    )


class FruitCountSample(Base):
    __tablename__ = "fruit_count_samples"
    __table_args__ = (
        CheckConstraint("apple_count >= 0", name="ck_fruit_count_samples_apple_count_non_negative"),
        Index("ix_fruit_count_samples_survey_id", "survey_id"),
    )

    id = Column(Integer, primary_key=True)
    survey_id = Column(Integer, ForeignKey("fruit_count_surveys.id"), nullable=False)
    tree_label = Column(String, nullable=True)
    apple_count = Column(Integer, nullable=False)
    notes = Column(String, nullable=True)

    survey = relationship("FruitCountSurvey", back_populates="samples")


class YearlyStats(Base):
    __tablename__ = "yearly_stats"
    __table_args__ = (
        CheckConstraint(
            "(field_id IS NOT NULL) + (planting_id IS NOT NULL) + (section_id IS NOT NULL) = 1",
            name="ck_yearly_stats_one_scope",
        ),
        CheckConstraint("season_year >= 1900", name="ck_yearly_stats_season_year"),
        CheckConstraint("thinning_hours IS NULL OR thinning_hours >= 0", name="ck_yearly_stats_thinning_hours"),
        CheckConstraint("harvest_hours IS NULL OR harvest_hours >= 0", name="ck_yearly_stats_harvest_hours"),
        CheckConstraint("filled_boxes IS NULL OR filled_boxes >= 0", name="ck_yearly_stats_filled_boxes"),
        CheckConstraint("yield_kg IS NULL OR yield_kg >= 0", name="ck_yearly_stats_yield_kg"),
        Index(
            "uq_yearly_stats_field_year",
            "field_id",
            "season_year",
            unique=True,
            sqlite_where=text("field_id IS NOT NULL"),
        ),
        Index(
            "uq_yearly_stats_planting_year",
            "planting_id",
            "season_year",
            unique=True,
            sqlite_where=text("planting_id IS NOT NULL"),
        ),
        Index(
            "uq_yearly_stats_section_year",
            "section_id",
            "season_year",
            unique=True,
            sqlite_where=text("section_id IS NOT NULL"),
        ),
    )

    id = Column(Integer, primary_key=True)
    season_year = Column(Integer, nullable=False)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=True)
    planting_id = Column(Integer, ForeignKey("plantings.id"), nullable=True)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=True)
    thinning_hours = Column(Float, nullable=True)
    harvest_hours = Column(Float, nullable=True)
    filled_boxes = Column(Float, nullable=True)
    yield_kg = Column(Float, nullable=True)
    revenue = Column(Float, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.datetime.now)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.datetime.now,
        onupdate=datetime.datetime.now,
    )

    field = relationship("Field", back_populates="yearly_stats")
    planting = relationship("Planting", back_populates="yearly_stats")
    section = relationship("Section", back_populates="yearly_stats")
