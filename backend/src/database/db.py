from .core import DatabaseCore
from .repositories import (
    FieldRepository,
    CropProtectionRepository,
    FieldWeatherRepository,
    FruitCountRepository,
    IrrigationRepository,
    NutrientRequirementRepository,
    PhenologyEventRepository,
    PlantingRepository,
    SectionRepository,
    TreatmentRepository,
    VarietyRepository,
    YearlyStatsRepository,
)
from .services import (
    FieldService,
    CropProtectionService,
    FruitCountService,
    IrrigationService,
    NutrientRequirementService,
    PhenologyEventService,
    PlantingService,
    SectionService,
    TreatmentImportService,
    YearlyStatsService,
)


class Database:
    def __init__(
        self,
        engine_url: str = "sqlite:///db/database.db",
        *,
        initialize_schema: bool = False,
        **engine_kwargs,
    ) -> None:
        self.core = DatabaseCore(
            engine_url=engine_url,
            initialize_schema=initialize_schema,
            **engine_kwargs,
        )
        self.engine = self.core.engine

        self.fields = FieldRepository()
        self.plantings = PlantingRepository(self.fields)
        self.sections = SectionRepository(self.plantings)
        self.phenology_events = PhenologyEventRepository(self.sections)
        self.varieties = VarietyRepository()
        self.nutrients = NutrientRequirementRepository(self.varieties)
        self.field_weather = FieldWeatherRepository(self.fields)
        self.fruit_counts = FruitCountRepository()
        self.irrigation = IrrigationRepository(self.fields)
        self.treatments = TreatmentRepository(self.sections)
        self.crop_protection = CropProtectionRepository()
        self.yearly_stats = YearlyStatsRepository()

        self.field_service = FieldService(
            self.core,
            self.fields,
        )
        self.irrigation_service = IrrigationService(
            self.core,
            self.fields,
            self.irrigation,
        )
        self.fruit_count_service = FruitCountService(
            self.core,
            self.fruit_counts,
        )
        self.planting_service = PlantingService(
            self.core,
            self.plantings,
        )
        self.nutrient_service = NutrientRequirementService(
            self.core,
            self.nutrients,
        )
        self.phenology_event_service = PhenologyEventService(
            self.core,
            self.phenology_events,
        )
        self.section_service = SectionService(
            self.core,
            self.sections,
        )
        self.treatment_import_service = TreatmentImportService(
            self.core,
            self.treatments,
        )
        self.crop_protection_service = CropProtectionService(
            self.core,
            self.crop_protection,
            self.field_weather,
        )
        self.yearly_stats_service = YearlyStatsService(
            self.core,
            self.yearly_stats,
        )

    def session_scope(self):
        return self.core.session_scope()

    def close(self) -> None:
        self.core.close()
