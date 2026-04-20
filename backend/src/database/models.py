import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import declarative_base, relationship

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
    water_balance = relationship(
        "WaterBalance",
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

    @property
    def field(self) -> Field | None:
        return self.planting.field if self.planting is not None else None

    @property
    def variety(self) -> "Variety | None":
        return self.planting.variety if self.planting is not None else None


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


class WaterBalance(Base):
    __tablename__ = "water_balance"
    __table_args__ = (
        UniqueConstraint("field_id", "date", name="uq_waterbalance_field_date"),
    )

    date = Column(Date, primary_key=True)
    field_id = Column(Integer, ForeignKey("fields.id"), primary_key=True)
    precipitation = Column(Float, nullable=False)
    irrigation = Column(Float, nullable=False)
    evapotranspiration = Column(Float, nullable=False)
    incoming = Column(Float, nullable=False)
    net = Column(Float, nullable=False)
    soil_water_content = Column(Float, nullable=False)
    available_water_storage = Column(Float, nullable=False)
    water_deficit = Column(Float, nullable=False)
    readily_available_water = Column(Float, nullable=True)
    safe_ratio = Column(Float, nullable=True)
    below_raw = Column(Boolean, nullable=True)

    field = relationship("Field", back_populates="water_balance")
