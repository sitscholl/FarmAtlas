from pydantic import BaseModel


class KcPhaseDefinition(BaseModel):
    name: str
    anchor: str


class PhenologicalStageDefinition(BaseModel):
    code: str
    label: str
    bbch_code: int | None
    principal_stage: int | None
    sort_order: int
    description: str
    kc_anchor: str | None = None
    default_duration: int | None = None


# Default durations are the Zanotelli et al. phase lengths in days:
# DOY 60->100, 100->166, 166->259, and 259->304.
PHENOLOGICAL_STAGES = [
    PhenologicalStageDefinition(
        code="BUD_BURST",
        label="Bud burst",
        bbch_code=53,
        principal_stage=5,
        sort_order=10,
        description="Green leaf tips enclosing flowers visible",
        kc_anchor="kc_ini_start",
        default_duration=40,
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
        sort_order=30,
        description="Fruit size up to 10 mm; fruit fall after flowering",
        kc_anchor="kc_dev_start",
        default_duration=66,
    ),
    PhenologicalStageDefinition(
        code="MAXIMUM_LAI",
        label="Maximum canopy",
        bbch_code=None,
        principal_stage=None,
        sort_order=40,
        description="Canopy considered fully developed for Kc purposes",
        kc_anchor="kc_mid_start",
        default_duration=93,
    ),
    PhenologicalStageDefinition(
        code="HARVEST_MATURITY",
        label="Harvest maturity",
        bbch_code=87,
        principal_stage=8,
        sort_order=50,
        description="Fruit ripe for picking",
        kc_anchor="kc_late_start",
        default_duration=45,
    ),
    PhenologicalStageDefinition(
        code="BEGIN_LEAF_FALL",
        label="Beginning leaf fall",
        bbch_code=93,
        principal_stage=9,
        sort_order=60,
        description="Beginning of leaf fall",
        kc_anchor="kc_end_start",
    ),
]

KC_PHASES = [
    KcPhaseDefinition(name="Kc_ini", anchor="kc_ini_start"),
    KcPhaseDefinition(name="Kc_dev", anchor="kc_dev_start"),
    KcPhaseDefinition(name="Kc_mid", anchor="kc_mid_start"),
    KcPhaseDefinition(name="Kc_late", anchor="kc_late_start"),
    KcPhaseDefinition(name="Kc_end", anchor="kc_end_start"),
]

PHENOLOGICAL_STAGES_BY_CODE = {stage.code: stage for stage in PHENOLOGICAL_STAGES}
PHENOLOGICAL_STAGES_BY_ANCHOR = {
    stage.kc_anchor: stage for stage in PHENOLOGICAL_STAGES if stage.kc_anchor is not None
}
KC_PHASES_BY_NAME = {phase.name: phase for phase in KC_PHASES}


def list_phenological_stages() -> list[PhenologicalStageDefinition]:
    return sorted(PHENOLOGICAL_STAGES, key=lambda stage: stage.sort_order)


def get_phenological_stage(code: str) -> PhenologicalStageDefinition | None:
    return PHENOLOGICAL_STAGES_BY_CODE.get(code)


def require_phenological_stage(code: str) -> PhenologicalStageDefinition:
    stage = get_phenological_stage(code)
    if stage is None:
        raise ValueError(f"No phenological stage with code {code!r} found")
    return stage
