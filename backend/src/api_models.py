from pydantic import BaseModel


class FieldContextResponse(BaseModel):
    id: int
    name: str
    reference_station: str
    soil_type: str
    humus_pct: float
    area_ha: float
    root_depth_cm: float
    p_allowable: float
