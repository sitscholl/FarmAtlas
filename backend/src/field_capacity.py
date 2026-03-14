from dataclasses import dataclass


@dataclass
class FieldCapacity:
    soil_type: str
    root_depth_cm: float
    humus_pct: float
    nfk_mm_per_dm: float
    nfk_total_mm: float

    def __post_init__(self) -> None:
        if self.root_depth_cm <= 0:
            raise ValueError("root_depth_cm must be > 0.")
        if self.nfk_mm_per_dm <= 0:
            raise ValueError("nfk_mm_per_dm must be > 0.")
        if self.nfk_total_mm <= 0:
            raise ValueError("nfk_total_mm must be > 0.")
        if self.humus_pct < 0:
            raise ValueError("humus_pct cannot be negative.")


DEFAULT_FIELD_CAPACITY_LOOKUP: dict[str, tuple[float, float]] = {
    "sand": (6, 12),
    "schwach lehmiger sand": (8, 14),
    "lehmiger sand": (12, 18),
    "schluffiger sand": (10, 16),
    "sandiger schluff": (20, 28),
    "schluff": (22, 30),
    "lehm": (18, 25),
    "sandiger lehm": (16, 22),
    "schluffiger lehm": (20, 28),
    "toniger lehm": (18, 26),
    "schluffiger ton": (18, 25),
    "ton": (15, 22),
    "humoser lehmiger sand": (14, 20),
}


def calculate_field_capacity(
    soil_type: str,
    humus_pct: float,
    root_depth_cm: float,
    custom_lookup: dict[str, tuple[float, float]] | None = None,
) -> FieldCapacity:
    lookup = custom_lookup or DEFAULT_FIELD_CAPACITY_LOOKUP
    soil_type_key = soil_type.lower()

    if soil_type_key not in lookup:
        raise KeyError(
            f"Soil type '{soil_type}' not found in lookup table. "
            "Use 'custom_lookup' or extend DEFAULT_FIELD_CAPACITY_LOOKUP."
        )

    nfk_min, nfk_max = lookup[soil_type_key]
    base_mm_per_dm = (nfk_min + nfk_max) / 2.0

    humus_extra = max(0.0, humus_pct - 1.5) * 1.5
    humus_extra = min(humus_extra, 6.0)

    nfk_mm_per_dm = base_mm_per_dm + humus_extra
    nfk_total_mm = nfk_mm_per_dm * (root_depth_cm / 10.0)

    return FieldCapacity(
        soil_type=soil_type,
        root_depth_cm=root_depth_cm,
        humus_pct=humus_pct,
        nfk_mm_per_dm=nfk_mm_per_dm,
        nfk_total_mm=nfk_total_mm,
    )
