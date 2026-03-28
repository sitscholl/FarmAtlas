/*
 * This file is auto-generated from the FastAPI OpenAPI schema.
 * Do not edit it manually. Run `npm run generate:types` in the frontend directory instead.
 */

export type FieldCreate = {
  name: string
  section?: string | null
  variety: string
  planting_year: number
  tree_count?: number | null
  tree_height?: number | null
  row_distance?: number | null
  tree_distance?: number | null
  running_metre?: number | null
  herbicide_free?: boolean | null
  active?: boolean
  reference_provider: string
  reference_station: string
  soil_type: string
  soil_weight?: string | null
  humus_pct: number
  area_ha: number
  effective_root_depth_cm: number
  p_allowable: number
}

export type FieldOverview = {
  water_balance_as_of: string | null
  current_water_deficit: number | null
  current_soil_water_content: number | null
  available_water_storage: number | null
  readily_available_water: number | null
  below_raw: boolean | null
  safe_ratio: number | null
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
  area_ha: number
  effective_root_depth_cm: number
  p_allowable: number
  id: number
}

export type FieldRead = {
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
  area_ha: number
  effective_root_depth_cm: number
  p_allowable: number
  id: number
}

export type FieldUpdate = {
  name: string
  section?: string | null
  variety: string
  planting_year: number
  tree_count?: number | null
  tree_height?: number | null
  row_distance?: number | null
  tree_distance?: number | null
  running_metre?: number | null
  herbicide_free?: boolean | null
  active?: boolean
  reference_provider: string
  reference_station: string
  soil_type: string
  soil_weight?: string | null
  humus_pct: number
  area_ha: number
  effective_root_depth_cm: number
  p_allowable: number
}

export type HTTPValidationError = {
  detail?: Array<ValidationError>
}

export type IrrigationCreate = {
  date: string
  method: string
  amount?: number
}

export type IrrigationRead = {
  date: string
  method: string
  amount: number
  id: number
  field_id: number
}

export type IrrigationUpdate = {
  date: string
  method: string
  amount?: number
  field_id: number
}

export type ValidationError = {
  loc: Array<string | number>
  msg: string
  type: string
  input?: unknown
  ctx?: {
}
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
  value_type: string | null
  model: string | null
}

export type WaterBalanceSummary = {
  field_id: number
  as_of: string | null
  current_water_deficit: number | null
  current_soil_water_content: number | null
  available_water_storage: number | null
  readily_available_water: number | null
  below_raw: boolean | null
  safe_ratio: number | null
}
