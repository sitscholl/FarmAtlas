export type FieldSummary = {
  id: number
  name: string
  section: string | null
  variety: string
  planting_year: number
  tree_count: number | null
  tree_height: number | null
  row_distance: number | null
  tree_distance: number | null
  running_metre: number | null
  herbicide_free: boolean | null
  active: boolean
  reference_provider: string
  reference_station: string
  soil_type: string
  soil_weight: string | null
  humus_pct: number
  area_ha: number | null
  effective_root_depth_cm: number
  p_allowable: number
}

export type FieldOverview = {
  id: number
  name: string
  section: string | null
  variety: string
  planting_year: number
  tree_count: number | null
  tree_height: number | null
  row_distance: number | null
  tree_distance: number | null
  running_metre: number | null
  herbicide_free: boolean | null
  active: boolean
  reference_provider: string
  reference_station: string
  soil_type: string
  soil_weight: string | null
  humus_pct: number
  area_ha: number | null
  effective_root_depth_cm: number
  p_allowable: number
  water_balance_as_of: string | null
  current_water_deficit: number | null
  current_soil_water_content: number | null
  available_water_storage: number | null
  readily_available_water: number | null
  below_raw: boolean | null
  safe_ratio: number | null
}

export type WaterBalanceSeriesPoint = {
  date: string
  precipitation: number
  irrigation: number
  evapotranspiration: number
  incoming: number
  net: number
  soil_water_content: number
  available_water_storage: number
  water_deficit: number
  readily_available_water: number | null
  safe_ratio: number | null
  below_raw: boolean | null
}
