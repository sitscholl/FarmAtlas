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
import datetime

Base = declarative_base()


class Field(Base):
    __tablename__ = "fields"
    __table_args__ = (
        Index(
            "uq_fields_identity",
            "name",
            text("coalesce(section, '')"),
            unique=True,
        ),
    )

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    section = Column(String, nullable=True)

    reference_provider = Column(String, nullable=False)
    reference_station = Column(String, nullable=False)

    soil_type = Column(String, nullable=True)
    soil_weight = Column(String, nullable=True)
    humus_pct = Column(Float, nullable=True)
    effective_root_depth_cm = Column(Float, nullable=True)
    p_allowable = Column(Float, nullable=True)  # Fraction depleted before stress.

    versions = relationship(
        "FieldVersion",
        back_populates="field",
        cascade="all, delete-orphan",
        order_by="FieldVersion.valid_from",
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

    def __repr__(self) -> str:
        return f"Field(id={self.id!r}, name={self.name!r})"

    @property
    def current_version(self) -> "FieldVersion | None":
        today = datetime.date.today()
        candidates = [
            version
            for version in self.versions
            if version.valid_from <= today and (version.valid_to is None or version.valid_to >= today)
        ]
        if candidates:
            return max(candidates, key=lambda version: version.valid_from)
        if self.versions:
            return max(self.versions, key=lambda version: version.valid_from)
        return None

    @property
    def variety(self) -> str | None:
        version = self.current_version
        return None if version is None or version.variety is None else version.variety.name

    @property
    def planting_year(self) -> int | None:
        version = self.current_version
        return None if version is None else version.planting_year

    @property
    def area_ha(self) -> float | None:
        version = self.current_version
        return None if version is None else version.area_ha

    @property
    def tree_count(self) -> int | None:
        version = self.current_version
        return None if version is None else version.tree_count

    @property
    def tree_height(self) -> float | None:
        version = self.current_version
        return None if version is None else version.tree_height

    @property
    def row_distance(self) -> float | None:
        version = self.current_version
        return None if version is None else version.row_distance

    @property
    def tree_distance(self) -> float | None:
        version = self.current_version
        return None if version is None else version.tree_distance

    @property
    def running_metre(self) -> float | None:
        version = self.current_version
        return None if version is None else version.running_metre

    @property
    def herbicide_free(self) -> bool | None:
        version = self.current_version
        return None if version is None else version.herbicide_free

    @property
    def active(self) -> bool:
        version = self.current_version
        return bool(version is not None and version.valid_to is None)


class FieldVersion(Base):
    __tablename__ = "field_versions"
    __table_args__ = (
        UniqueConstraint("field_id", "valid_from", name="uq_field_versions_field_valid_from"),
        CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_field_versions_valid_range",
        ),
        Index(
            "uq_field_versions_open_ended",
            "field_id",
            unique=True,
            sqlite_where=text("valid_to IS NULL"),
        ),
    )

    id = Column(Integer, primary_key=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False)
    variety_id = Column(Integer, ForeignKey("varieties.id"), nullable=False)
    planting_year = Column(Integer, nullable=False)
    area_ha = Column(Float, nullable=False)
    tree_count = Column(Integer, nullable=True)
    tree_height = Column(Float, nullable=True)
    row_distance = Column(Float, nullable=True)
    tree_distance = Column(Float, nullable=True)
    running_metre = Column(Float, nullable=True)
    herbicide_free = Column(Boolean, nullable=True)

    valid_from = Column(Date, nullable=False)
    valid_to = Column(Date, nullable=True)

    field = relationship("Field", back_populates="versions")
    variety = relationship("Variety", back_populates="field_versions")

    def __repr__(self) -> str:
        return f"FieldVersion(id={self.id!r}, field_id={self.field_id!r}, valid_from={self.valid_from!r})"


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

    field_versions = relationship("FieldVersion", back_populates="variety")
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
    requirement_per_kg_yield = Column(Float, nullable=False)

    variety = relationship("Variety", back_populates="nutrient_requirements")


class Irrigation(Base):
    __tablename__ = "irrigation_events"

    id = Column(Integer, primary_key=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False)
    date = Column(Date, nullable=False)
    method = Column(String, nullable=False)
    amount = Column(Float, default=100)

    field = relationship("Field", back_populates="irrigation_events")

    __table_args__ = (UniqueConstraint("field_id", "date", name="uq_irrigation_field_date"),)

    def __repr__(self) -> str:
        return f"Irrigation(id={self.id!r}, field_id={self.field_id!r}, date={self.date!r})"


class WaterBalance(Base):
    __tablename__ = "water_balance"

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
    below_raw = Column(Float, nullable=True)

    field = relationship("Field", back_populates="water_balance")

    __table_args__ = (UniqueConstraint("field_id", "date", name="uq_waterbalance_field_date"),)
