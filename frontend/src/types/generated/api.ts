/*
 * This file is auto-generated from the FastAPI OpenAPI schema.
 * Do not edit it manually. Run `npm run generate:types` in the frontend directory instead.
 */

export type FieldCreate = {
  group: string
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
  soil_type?: string | null
  soil_weight?: string | null
  humus_pct?: number | null
  area_ha: number
  effective_root_depth_cm?: number | null
  p_allowable?: number | null
  drip_distance?: number | null
  drip_discharge?: number | null
  tree_strip_width?: number | null
}

export type FieldOverview = {
  water_balance_as_of: string | null
  current_water_deficit: number | null
  current_soil_water_content: number | null
  available_water_storage: number | null
  readily_available_water: number | null
  below_raw: boolean | null
  safe_ratio: number | null
  group: string
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
  soil_type?: string | null
  soil_weight?: string | null
  humus_pct?: number | null
  area_ha: number
  effective_root_depth_cm?: number | null
  p_allowable?: number | null
  drip_distance?: number | null
  drip_discharge?: number | null
  tree_strip_width?: number | null
  id: number
  valid_from: string
  valid_to?: string | null
}

export type FieldRead = {
  group: string
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
  soil_type?: string | null
  soil_weight?: string | null
  humus_pct?: number | null
  area_ha: number
  effective_root_depth_cm?: number | null
  p_allowable?: number | null
  drip_distance?: number | null
  drip_discharge?: number | null
  tree_strip_width?: number | null
  id: number
  valid_from: string
  valid_to?: string | null
}

export type FieldReadGrouped = {
  fields: Array<FieldReadGroupedField>
}

export type FieldReadGroupedField = {
  name: string
  active: boolean
  field_ids: Array<number>
  varieties: Array<FieldReadGroupedVariety>
}

export type FieldReadGroupedSection = {
  section?: string | null
  field: FieldRead
}

export type FieldReadGroupedVariety = {
  variety: string
  field_ids: Array<number>
  sections: Array<FieldReadGroupedSection>
}

export type FieldReplant = {
  group: string
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
  soil_type?: string | null
  soil_weight?: string | null
  humus_pct?: number | null
  area_ha: number
  effective_root_depth_cm?: number | null
  p_allowable?: number | null
  drip_distance?: number | null
  drip_discharge?: number | null
  tree_strip_width?: number | null
  valid_from: string
}

export type FieldUpdate = {
  group: string
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
  soil_type?: string | null
  soil_weight?: string | null
  humus_pct?: number | null
  area_ha: number
  effective_root_depth_cm?: number | null
  p_allowable?: number | null
  drip_distance?: number | null
  drip_discharge?: number | null
  tree_strip_width?: number | null
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

export type IrrigationCommandCreate = {
  field: string
  date?: string | null
  method: string
  duration: number
  amount?: number | null
}

export type IrrigationCommandResult = {
  success: boolean
  status: string
  message: string
  field: string
  date: string
  method: string
  duration: number
  amount: number | null
  matched_field_ids: Array<number>
  error?: string | null
  created_event_ids: Array<number>
  updated_event_ids: Array<number>
  unchanged_event_ids: Array<number>
  created_count: number
  updated_count: number
  unchanged_count: number
}

export type IrrigationCreate = {
  date: string
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

export type IrrigationTarget = {
  field: string
  active: boolean
  field_ids: Array<number>
  field_count: number
  sections?: Array<string>
  varieties?: Array<string>
}

export type IrrigationUpdate = {
  date: string
  method: string
  duration: number
  amount?: number | null
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
