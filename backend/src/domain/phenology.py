from pydantic import BaseModel

class PhenologicalStageDefinition(BaseModel):
    code: str
    label: str
    bbch_code: int | None
    principal_stage: int | None
    sort_order: int
    description: str
    kc_anchor: str | None = None
    default_duration: int | None = None

PHENOLOGICAL_STAGES = [
    PhenologicalStageDefinition(
        code="BUD_BURST",
        label="Bud burst",
        bbch_code=53,
        principal_stage=5,
        sort_order=10,
        description="Green leaf tips enclosing flowers visible",
        kc_anchor="kc_ini_start",
    ),
    PhenologicalStageDefinition(
        code="FLOWERING",
        label="Flowering",
        bbch_code=65,
        principal_stage=6,
        sort_order=20,
        description=r"Full flowering: at least 50% of flowers open, first petals falling",
        kc_anchor=None,
    ),
    PhenologicalStageDefinition(
        code="FRUIT_SET",
        label="Fruit set",
        bbch_code=71,
        principal_stage=7,
        sort_order=20,
        description="Fruit size up to 10 mm; fruit fall after flowering",
        kc_anchor="kc_dev_start",
    ),
    PhenologicalStageDefinition(
        code="MAXIMUM_LAI",
        label="Maximum canopy",
        bbch_code=None,
        principal_stage=None,
        sort_order=30,
        description="Canopy considered fully developed for Kc purposes",
        kc_anchor="kc_mid_start",
    ),
    PhenologicalStageDefinition(
        code="HARVEST_MATURITY",
        label="Harvest maturity",
        bbch_code=87,
        principal_stage=8,
        sort_order=40,
        description="Fruit ripe for picking",
        kc_anchor="kc_late_start",
    ),
    PhenologicalStageDefinition(
        code="BEGIN_LEAF_FALL",
        label="Beginning leaf fall",
        bbch_code=93,
        principal_stage=9,
        sort_order=50,
        description="Beginning of leaf fall",
        kc_anchor="kc_end_start",
    ),
]
