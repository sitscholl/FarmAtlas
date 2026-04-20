from .core import DatabaseCore
from .repositories import (
    FieldRepository,
    IrrigationRepository,
    NutrientRequirementRepository,
    PlantingRepository,
    SectionRepository,
    VarietyRepository,
    WaterBalanceRepository,
)
from .services import FieldService, IrrigationService, NutrientRequirementService, PlantingService, SectionService


class Database:
    WATER_BALANCE_TRIGGER_FIELDS = {
        "soil_type",
        "soil_weight",
        "humus_pct",
        "effective_root_depth_cm",
        "p_allowable",
        "reference_provider",
        "reference_station",
    }

    def __init__(self, engine_url: str = "sqlite:///db/database.db", **engine_kwargs) -> None:
        self.core = DatabaseCore(engine_url=engine_url, **engine_kwargs)
        self.engine = self.core.engine

        self.fields = FieldRepository()
        self.plantings = PlantingRepository(self.fields)
        self.sections = SectionRepository(self.plantings)
        self.varieties = VarietyRepository()
        self.nutrients = NutrientRequirementRepository(self.varieties)
        self.water_balance = WaterBalanceRepository(self.fields)
        self.irrigation = IrrigationRepository(self.fields)

        self.field_service = FieldService(
            self.core,
            self.fields,
            self.water_balance,
            water_balance_trigger_fields=self.WATER_BALANCE_TRIGGER_FIELDS,
        )
        self.irrigation_service = IrrigationService(
            self.core,
            self.fields,
            self.irrigation,
            self.water_balance,
        )
        self.planting_service = PlantingService(
            self.core,
            self.plantings,
        )
        self.nutrient_service = NutrientRequirementService(
            self.core,
            self.nutrients,
        )
        self.section_service = SectionService(
            self.core,
            self.sections,
        )

    def session_scope(self):
        return self.core.session_scope()

    def close(self) -> None:
        self.core.close()
