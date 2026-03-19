from dataclasses import dataclass
from typing import Literal


SoilWeight = Literal["sehr leicht", "leicht", "mittel", "schwer"]


@dataclass(frozen=True)
class SoilTypeDefaults:
    """
    Default storage lookup for a topsoil texture class.

    Notes
    -----
    - nfk_range_mm_per_dm is intended as *plant-available water storage*
      (usable storage, similar to nFK / available water), not strict field
      capacity in the soil-physics sense.
    - humus_factor_mm_per_dm_per_pct controls how strongly humus increases
      storage above the baseline threshold.
    - humus_cap_mm_per_dm limits the humus bonus so values do not become
      unrealistically large.
    """
    nfk_range_mm_per_dm: tuple[float, float]
    humus_factor_mm_per_dm_per_pct: float
    humus_cap_mm_per_dm: float
    notes: tuple[str, ...] = ()


@dataclass
class SoilWaterEstimate:
    soil_type: str
    soil_weight: str | None
    humus_pct: float
    effective_root_depth_cm: float
    coarse_fragments_pct: float
    nfk_base_mm_per_dm: float
    humus_bonus_mm_per_dm: float
    nfk_mm_per_dm: float
    nfk_total_mm: float
    nfk_conservative_mm: float
    nfk_optimistic_mm: float
    uncertainty_mm: float

    def __post_init__(self) -> None:
        if self.effective_root_depth_cm <= 0:
            raise ValueError("effective_root_depth_cm must be > 0.")
        if self.humus_pct < 0:
            raise ValueError("humus_pct cannot be negative.")
        if not 0 <= self.coarse_fragments_pct <= 100:
            raise ValueError("coarse_fragments_pct must be between 0 and 100.")
        if self.nfk_mm_per_dm <= 0:
            raise ValueError("nfk_mm_per_dm must be > 0.")
        if self.nfk_total_mm <= 0:
            raise ValueError("nfk_total_mm must be > 0.")
        if self.uncertainty_mm < 0:
            raise ValueError("uncertainty_mm must be >= 0.")


DEFAULT_SOIL_DEFAULTS: dict[str, SoilTypeDefaults] = {
    "sand": SoilTypeDefaults((6, 12), 1.6, 5.5, ("very low storage, drains quickly",)),
    "schwach lehmiger sand": SoilTypeDefaults((8, 14), 1.5, 5.5),
    "lehmiger sand": SoilTypeDefaults((12, 18), 1.4, 5.0),
    "humoser lehmiger sand": SoilTypeDefaults((14, 20), 1.35, 6.0, ("organic matter matters strongly here",)),
    "schluffiger sand": SoilTypeDefaults((10, 16), 1.25, 4.5),
    "sandiger schluff": SoilTypeDefaults((20, 28), 1.0, 4.0),
    "schluff": SoilTypeDefaults((22, 30), 0.9, 4.0),
    "sandiger lehm": SoilTypeDefaults((16, 22), 1.0, 4.0),
    "lehm": SoilTypeDefaults((18, 25), 0.9, 4.0),
    "schluffiger lehm": SoilTypeDefaults((20, 28), 0.85, 3.5),
    "toniger lehm": SoilTypeDefaults((18, 26), 0.75, 3.0),
    "schluffiger ton": SoilTypeDefaults((18, 25), 0.65, 3.0),
    "ton": SoilTypeDefaults((15, 22), 0.5, 2.5, ("high total water, but less plant-available",)),
}


SOIL_WEIGHT_POSITION: dict[str, float] = {
    "sehr leicht": 0.25,
    "leicht": 0.25,
    "mittel": 0.50,
    "schwer": 0.75,
}


def _normalize_text(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _pick_value_from_range(value_range: tuple[float, float], soil_weight: str | None) -> float:
    low, high = value_range
    if low > high:
        raise ValueError(f"Invalid range: {value_range}")

    if soil_weight is None:
        position = 0.50
    else:
        key = _normalize_text(soil_weight)
        if key not in SOIL_WEIGHT_POSITION:
            valid = ", ".join(sorted(SOIL_WEIGHT_POSITION))
            raise ValueError(f"Unknown soil_weight '{soil_weight}'. Expected one of: {valid}")
        position = SOIL_WEIGHT_POSITION[key]

    return low + (high - low) * position


def _estimate_humus_bonus(
    soil_defaults: SoilTypeDefaults,
    humus_pct: float,
    baseline_humus_pct: float = 1.5,
) -> float:
    # Only count humus above a modest baseline.
    effective_humus = max(0.0, humus_pct - baseline_humus_pct)
    bonus = effective_humus * soil_defaults.humus_factor_mm_per_dm_per_pct
    return min(bonus, soil_defaults.humus_cap_mm_per_dm)


def estimate_available_water_storage_capacity(
    soil_type: str,
    humus_pct: float,
    effective_root_depth_cm: float,
    soil_weight: str | None = None,
    coarse_fragments_pct: float = 0.0,
    custom_defaults: dict[str, SoilTypeDefaults] | None = None,
) -> SoilWaterEstimate:
    """
    Estimate plant-available water storage for a homogeneous profile.

    Parameters
    ----------
    soil_type:
        German texture label, e.g. "humoser lehmiger Sand".
    humus_pct:
        Humus / organic matter in percent.
    effective_root_depth_cm:
        Effective rooting depth for water uptake, not the maximum possible root depth.
    soil_weight:
        Optional qualitative modifier: 'leicht', 'mittel', 'schwer'.
        This is used to place the estimate within the default lookup range.
    coarse_fragments_pct:
        Volume percent gravel / stones / coarse fragments. Reduces fine-earth water storage.
    custom_defaults:
        Optional lookup override.

    Returns
    -------
    SoilWaterEstimate
        Estimate including conservative and optimistic totals and notes.
    """
    if humus_pct < 0:
        raise ValueError("humus_pct cannot be negative.")
    if effective_root_depth_cm <= 0:
        raise ValueError("effective_root_depth_cm must be > 0.")
    if not 0 <= coarse_fragments_pct <= 100:
        raise ValueError("coarse_fragments_pct must be between 0 and 100.")

    lookup = custom_defaults or DEFAULT_SOIL_DEFAULTS
    soil_key = _normalize_text(soil_type)

    if soil_key not in lookup:
        known = ", ".join(sorted(lookup))
        raise KeyError(
            f"Soil type '{soil_type}' not found in lookup table. "
            f"Known soil types: {known}"
        )

    defaults = lookup[soil_key]
    nfk_base_mm_per_dm = _pick_value_from_range(defaults.nfk_range_mm_per_dm, soil_weight)
    humus_bonus_mm_per_dm = _estimate_humus_bonus(defaults, humus_pct)

    coarse_factor = 1.0 - (coarse_fragments_pct / 100.0)
    nfk_mm_per_dm = (nfk_base_mm_per_dm + humus_bonus_mm_per_dm) * coarse_factor
    depth_dm = effective_root_depth_cm / 10.0
    nfk_total_mm = nfk_mm_per_dm * depth_dm

    # Uncertainty: keep it transparent rather than pretending to be exact.
    low_raw, high_raw = defaults.nfk_range_mm_per_dm
    low_total = (low_raw + humus_bonus_mm_per_dm) * coarse_factor * depth_dm
    high_total = (high_raw + humus_bonus_mm_per_dm) * coarse_factor * depth_dm

    # Add a small structural uncertainty term for profile heterogeneity.
    structural_uncertainty_mm = max(5.0, 0.08 * nfk_total_mm)
    conservative = max(0.0, low_total - structural_uncertainty_mm)
    optimistic = high_total + structural_uncertainty_mm
    uncertainty_mm = max(abs(nfk_total_mm - conservative), abs(optimistic - nfk_total_mm))

    return SoilWaterEstimate(
        soil_type=soil_type,
        soil_weight=soil_weight,
        humus_pct=humus_pct,
        effective_root_depth_cm=effective_root_depth_cm,
        coarse_fragments_pct=coarse_fragments_pct,
        nfk_base_mm_per_dm=nfk_base_mm_per_dm,
        humus_bonus_mm_per_dm=humus_bonus_mm_per_dm,
        nfk_mm_per_dm=nfk_mm_per_dm,
        nfk_total_mm=nfk_total_mm,
        nfk_conservative_mm=conservative,
        nfk_optimistic_mm=optimistic,
        uncertainty_mm=uncertainty_mm,
    )

if __name__ == "__main__":
    samples = [
        {
            "soil_type": "humoser lehmiger Sand",
            "soil_weight": "leicht",
            "humus_pct": 5.9,
            "effective_root_depth_cm": 60,
        },
        {
            "soil_type": "humoser lehmiger Sand",
            "soil_weight": "leicht",
            "humus_pct": 5.8,
            "effective_root_depth_cm": 60,
        },
    ]

    for sample in samples:
        result = estimate_available_water_storage_capacity(**sample)
        print(f"{sample['soil_type']} | humus={sample['humus_pct']}%")
        print(f"  base nFK:      {result.nfk_base_mm_per_dm:.1f} mm/dm")
        print(f"  humus bonus:   {result.humus_bonus_mm_per_dm:.1f} mm/dm")
        print(f"  final nFK:     {result.nfk_mm_per_dm:.1f} mm/dm")
        print(f"  total storage: {result.nfk_total_mm:.1f} mm")
        print(f"  range:         {result.nfk_conservative_mm:.1f}..{result.nfk_optimistic_mm:.1f} mm")
        print()
