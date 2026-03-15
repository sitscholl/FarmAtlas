export type FieldSummary = {
  id: number
  name: string
  reference_station: string
  soil_type: string
  humus_pct: number
  area_ha: number | null
  root_depth_cm: number
  p_allowable: number
}

export type FieldOverview = {
  id: number
  name: string
  reference_station: string
  soil_type: string
  humus_pct: number
  area_ha: number | null
  root_depth_cm: number
  p_allowable: number
  water_balance_as_of: string | null
  current_deficit: number | null
  current_soil_storage: number | null
  field_capacity: number | null
  readily_available_water: number | null
  below_raw: boolean | null
  safe_ratio: number | null
}
