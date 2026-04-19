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

class _AggregatedAttrs:
    @property
    def variety(self) -> str | None:
        if hasattr(self, 'plantings'):
            pass
        else:
            return self.variety
    @property
    def area(self) -> float | None:
        return (sum(float(i.area) for i in self.sections)) 
    @property
    def tree_count(self) -> str | None:
        return (sum(float(i.tree_count) for i in self.sections)) 
    #add other atributes that should be aggregated

class _DerivedAttrs:
    @property
    def elevation(self):
        if hasattr(self, 'field'):
            return self.field.elevation
        else:
            return None

class Field(Base, _AggregatedAttrs):
    __tablename__ = "fields"
    __table_args__ = (
        Index(
            "uq_fields_identity",
            "name",
            text("coalesce(section, '')"),
            "variety_id",
            "planting_year",
            unique=True,
        ),
        Index(
            "ix_fields_name_section",
            "name",
            text("coalesce(section, '')"),
        ),
        CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_fields_valid_range",
        ),
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
    drip_distance = Column(Float, nullable=True) #Distance between drip holes in tube
    drip_discharge = Column(Float, nullable=True) #amount of water going out from one drip hole in liter per hour
    tree_strip_width = Column(Float, nullable=True) #width of the area below each drip tube to consider when calculating irrigation amount
    valve_open = Column(Boolean, default = True, nullable = False) #no irrigation possible when false

    plantings = relationship(
        "Planting",
        back_populates='field',
        cascade="all, delete-orphan",
    )
    sections = relationship(
        "Section",
        back_populates='field',
        cascade="all, delete-orphan",
    )
    parcels = relationship(
        "CadastralParcel",
        back_populates='field',
        cascade="all, delete-orphan",
    )
    varieties = relationship(
        "Variety",
        back_populates='fields',
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

class Planting(Base, _AggregatedAttrs, _DerivedAttrs):
    __tablename__ = "planting"

    id = Column(Integer, primary_key=True)
    field_id = Column(Integer, ForeignKey('fields.id'), nullable = False)
    variety_id = Column(Integer, ForeignKey("varieties.id"), nullable=False)

    field = relationship("Field", back_populates='plantings')
    variety = relationship("Variety", back_populates="plantings")
    sections = relationship("Section", back_populates="planting")

class Section(Base, _DerivedAttrs):
    __tablename__ = "section"

    id = Column(Integer, primary_key=True)
    planting_id = Column(Integer, ForeignKey('planting.id'), nullable=False)
    
    planting_year = Column(Integer, nullable=False)
    area = Column(Float, nullable=False)  #in m²; landw. nuttzfl von katasterliste, entspricht lafis fläche
    tree_count = Column(Integer, nullable=True)
    tree_height = Column(Float, nullable=True)
    row_distance = Column(Float, nullable=True)
    tree_distance = Column(Float, nullable=True)
    running_metre = Column(Float, nullable=True)
    herbicide_free = Column(Boolean, nullable=True)
    
    valid_from = Column(Date, nullable=False)
    valid_to = Column(Date, nullable=True)

    field = relationship("Field", back_populates='sections')
    planting = relationship("Planting", back_populates='sections')
    variety = relationship("Variety", back_populates="sections")

    @property
    def active(self) -> bool:
        today = datetime.date.today()
        return self.valid_from <= today and (self.valid_to is None or self.valid_to >= today)

class CadastralParcel(Base, _DerivedAttrs):
    __tablename__ = 'cadastral_parcel'

    id = Column(Integer, primary_key=True)
    field_id = Column(Integer, ForeignKey('fields.id'), nullable = False)

    parcel_id = Column(String, nullable = False)
    municipality_id = Column(String, nullable = False)
    area = Column(Float, nullable = False)

    field = relationship("Field", back_populates='parcels')

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

    fields = relationship("Field", back_populates="varieties")
    plantings = relationship("Planting", back_populates='variety')
    sections = relationship("Section", back_populates='variety')
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
    duration = Column(Float, nullable = False)
    amount = Column(Float, nullable = False) #amount of irrigation water in mm

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
