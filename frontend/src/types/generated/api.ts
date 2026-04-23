/*
 * This file is auto-generated from the FastAPI OpenAPI schema.
 * Do not edit it manually. Run `npm run generate:types` in the frontend directory instead.
 */

export type CadastralParcelRead = {
  id: number
  field_id: number
  parcel_id: string
  municipality_id: string
  area: number
}

export type FieldCreate = {
  group: string
  name: string
  reference_provider: string
  reference_station: string
  elevation: number
  soil_type?: string | null
  soil_weight?: string | null
  humus_pct?: number | null
  effective_root_depth_cm?: number | null
  p_allowable?: number | null
  drip_distance?: number | null
  drip_discharge?: number | null
  tree_strip_width?: number | null
  valve_open?: boolean
}

export type FieldDetailRead = {
  field: FieldRead
  cadastral_parcels: Array<CadastralParcelRead>
  plantings: Array<PlantingDetailRead>
}

export type FieldRead = {
  id: number
  group: string
  name: string
  reference_provider: string
  reference_station: string
  elevation: number
  soil_type?: string | null
  soil_weight?: string | null
  humus_pct?: number | null
  effective_root_depth_cm?: number | null
  p_allowable?: number | null
  drip_distance?: number | null
  drip_discharge?: number | null
  tree_strip_width?: number | null
  valve_open: boolean
}

export type FieldSummaryRead = {
  id: number
  group: string
  name: string
  reference_provider: string
  reference_station: string
  elevation: number
  soil_type?: string | null
  soil_weight?: string | null
  humus_pct?: number | null
  effective_root_depth_cm?: number | null
  p_allowable?: number | null
  drip_distance?: number | null
  drip_discharge?: number | null
  tree_strip_width?: number | null
  valve_open: boolean
  total_area: number
  tree_count?: number | null
  running_metre?: number | null
  active: boolean
  herbicide_free?: boolean | null
  planting_count: number
  section_count: number
  variety_names: Array<string>
  section_names: Array<string>
  planting_year_min?: number | null
  planting_year_max?: number | null
  last_irrigation_date?: string | null
  water_balance_summary: WaterBalanceSummary
}

export type FieldUpdate = {
  group: string
  name: string
  reference_provider: string
  reference_station: string
  elevation: number
  soil_type?: string | null
  soil_weight?: string | null
  humus_pct?: number | null
  effective_root_depth_cm?: number | null
  p_allowable?: number | null
  drip_distance?: number | null
  drip_discharge?: number | null
  tree_strip_width?: number | null
  valve_open?: boolean
}

export type HTTPValidationError = {
  detail?: Array<ValidationError>
}

export type IrrigationBulkCreate = {
  date: string
  method: string
  duration: number
  amount?: number | null
  field_ids: Array<number>
}

export type IrrigationBulkResponse = {
  created_event_ids: Array<number>
  created_count: number
  skipped_field_ids: Array<number>
  errors_by_field_id?: {
  [key: string]: string
}
}

export type IrrigationBulkUpsertResponse = {
  created_event_ids: Array<number>
  updated_event_ids: Array<number>
  unchanged_event_ids: Array<number>
  created_count: number
  updated_count: number
  unchanged_count: number
  skipped_field_ids: Array<number>
  errors_by_field_id?: {
  [key: string]: string
}
}

export type IrrigationCreate = {
  date: string
  method: string
  duration: number
  amount?: number | null
}

export type IrrigationFieldNameUpsert = {
  field: string
  date?: string
  method: string
  duration: number
  amount?: number | null
}

export type IrrigationRead = {
  date: string
  method: string
  duration: number
  amount: number
  id: number
  field_id: number
}

export type IrrigationUpdate = {
  date: string
  method: string
  duration: number
  amount?: number | null
  field_id: number
}

export type NutrientRequirementCreate = {
  variety?: string | null
  nutrient_code: string
  requirement_per_kg_min: number
  requirement_per_kg_mean: number
  requirement_per_kg_max: number
}

export type NutrientRequirementRead = {
  id: number
  variety?: string | null
  nutrient_code: string
  requirement_per_kg_min: number
  requirement_per_kg_mean: number
  requirement_per_kg_max: number
}

export type NutrientRequirementUpdate = {
  variety?: string | null
  nutrient_code: string
  requirement_per_kg_min: number
  requirement_per_kg_mean: number
  requirement_per_kg_max: number
}

export type PlantingCreate = {
  field_id: number
  variety: string
  valid_from: string
  valid_to?: string | null
}

export type PlantingDetailRead = {
  id: number
  field_id: number
  variety: string
  valid_from: string
  valid_to?: string | null
  active: boolean
  sections: Array<SectionRead>
}

export type PlantingRead = {
  id: number
  field_id: number
  variety: string
  valid_from: string
  valid_to?: string | null
  active: boolean
}

export type PlantingUpdate = {
  variety: string
  valid_from: string
  valid_to?: string | null
}

export type SectionCreate = {
  planting_id: number
  name: string
  planting_year: number
  area: number
  tree_count?: number | null
  tree_height?: number | null
  row_distance?: number | null
  tree_distance?: number | null
  running_metre?: number | null
  herbicide_free?: boolean | null
  valid_from: string
  valid_to?: string | null
}

export type SectionRead = {
  id: number
  planting_id: number
  name: string
  planting_year: number
  area: number
  tree_count?: number | null
  tree_height?: number | null
  row_distance?: number | null
  tree_distance?: number | null
  running_metre?: number | null
  herbicide_free?: boolean | null
  valid_from: string
  valid_to?: string | null
  active: boolean
}

export type SectionUpdate = {
  name: string
  planting_year: number
  area: number
  tree_count?: number | null
  tree_height?: number | null
  row_distance?: number | null
  tree_distance?: number | null
  running_metre?: number | null
  herbicide_free?: boolean | null
  valid_from: string
  valid_to?: string | null
}

export type ValidationError = {
  loc: Array<string | number>
  msg: string
  type: string
  input?: unknown
  ctx?: {
}
}

export type VarietyCreate = {
  name: string
  group: string
  nr_per_kg?: number | null
  kg_per_box?: number | null
  slope?: number | null
  intercept?: number | null
  specific_weight?: number | null
}

export type VarietyRead = {
  name: string
  group: string
  nr_per_kg?: number | null
  kg_per_box?: number | null
  slope?: number | null
  intercept?: number | null
  specific_weight?: number | null
  id: number
}

export type VarietyUpdate = {
  name: string
  group: string
  nr_per_kg?: number | null
  kg_per_box?: number | null
  slope?: number | null
  intercept?: number | null
  specific_weight?: number | null
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
