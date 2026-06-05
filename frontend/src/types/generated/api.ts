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

export type CropProtectionFieldSummaryRead = {
  field_id: number
  field_name: string
  status: string
  evaluation_count: number
  status_counts: {
  [key: string]: number
}
  evaluations: Array<CropProtectionRuleEvaluationRead>
}

export type CropProtectionMetricEvaluationRead = {
  metric_type: string
  value: number | number | null
  threshold: number
  warning_threshold?: number | null
  status: string
}

export type CropProtectionRuleCreate = {
  name: string
  enabled?: boolean
  season_start?: string | null
  season_end?: string | null
  logic?: "any" | "all"
  notes?: string | null
  product_names: Array<string>
  scopes: Array<CropProtectionRuleScopeBase>
  metrics: Array<CropProtectionRuleMetricBase>
}

export type CropProtectionRuleEvaluationRead = {
  rule_id: number
  rule_name: string
  section_id: number
  section_name: string
  field_id: number
  field_name: string
  status: string
  last_treatment_date?: string | null
  last_treatment_product?: string | null
  metrics: Array<CropProtectionMetricEvaluationRead>
}

export type CropProtectionRuleMetricBase = {
  metric_type: "days_since" | "rain_since" | "gdd_since"
  enabled?: boolean
  threshold: number
  warning_threshold?: number | null
  metric_config?: {
  [key: string]: unknown
}
}

export type CropProtectionRuleMetricRead = {
  metric_type: "days_since" | "rain_since" | "gdd_since"
  enabled?: boolean
  threshold: number
  warning_threshold?: number | null
  metric_config?: {
  [key: string]: unknown
}
  id: number
}

export type CropProtectionRuleProductRead = {
  id: number
  product_name: string
}

export type CropProtectionRuleRead = {
  id: number
  name: string
  enabled: boolean
  season_start?: string | null
  season_end?: string | null
  logic: "any" | "all"
  notes?: string | null
  products: Array<CropProtectionRuleProductRead>
  scopes: Array<CropProtectionRuleScopeRead>
  metrics: Array<CropProtectionRuleMetricRead>
}

export type CropProtectionRuleScopeBase = {
  scope_type: "field" | "planting" | "section"
  scope_id: number
}

export type CropProtectionRuleScopeRead = {
  scope_type: "field" | "planting" | "section"
  scope_id: number
  id: number
}

export type CropProtectionRuleUpdate = {
  name: string
  enabled?: boolean
  season_start?: string | null
  season_end?: string | null
  logic?: "any" | "all"
  notes?: string | null
  product_names: Array<string>
  scopes: Array<CropProtectionRuleScopeBase>
  metrics: Array<CropProtectionRuleMetricBase>
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
  current_phenology?: string | null
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

export type FieldWeatherBulkRefreshResponse = {
  start: string
  end: string
  refreshed: Array<FieldWeatherRefreshResponse>
  failed_field_ids: Array<number>
  errors_by_field_id: {
  [key: string]: string
}
  total_upserted_count: number
}

export type FieldWeatherDailyRead = {
  date: string
  field_id: number
  precipitation: number
  tmin?: number | null
  tmax?: number | null
  tmean?: number | null
  source_provider: string
  source_station: string
  value_type: string
}

export type FieldWeatherRefreshResponse = {
  field_id: number
  start: string
  end: string
  upserted_count: number
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

export type PhenologicalStageDefinition = {
  code: string
  label: string
  bbch_code: number | null
  principal_stage: number | null
  sort_order: number
  description: string
  kc_anchor?: string | null
  default_duration?: number | null
}

export type PhenologyBulkCreate = {
  section_ids: Array<number>
  stage_code: string
  date: string
}

export type PhenologyBulkResponse = {
  created_event_ids: Array<number>
  created_count: number
  skipped_section_ids: Array<number>
  errors_by_section_id?: {
  [key: string]: string
}
}

export type PhenologyEventCreate = {
  section_id: number
  stage_code: string
  date: string
}

export type PhenologyEventRead = {
  id: number
  section_id: number
  stage_code: string
  date: string
  stage_name: string
  bbch_code?: number | null
  principal_stage?: number | null
  kc_anchor?: string | null
}

export type PhenologyEventUpdate = {
  section_id: number
  stage_code: string
  date: string
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
  current_phenology?: string | null
  phenology_events?: Array<PhenologyEventRead>
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

export type TreatmentCsvImportResponse = {
  import_summary: TreatmentImportRead
  unresolved_external_section_names: Array<string>
}

export type TreatmentEventRead = {
  id: number
  source: string
  season_year: number
  date: string
  external_section_name: string
  section_id?: number | null
  product_name: string
  reason?: string | null
  dose_per_hl?: number | null
  hl?: number | null
  cost?: number | null
  row_hash: string
  resolution_status: string
}

export type TreatmentImportRead = {
  id: number
  source: string
  season_year: number
  imported_at: string
  row_count: number
  unresolved_count: number
}

export type TreatmentSectionAliasCreate = {
  source?: string
  external_section_name: string
  section_id: number
}

export type TreatmentSectionAliasRead = {
  source?: string
  external_section_name: string
  section_id: number
  id: number
}

export type TreatmentSectionAliasUpdate = {
  source?: string
  external_section_name: string
  section_id: number
}

export type ValidationError = {
  loc: Array<string | number>
  msg: string
  type: string
  input?: unknown
  ctx?: Record<string, never>
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
  kc?: number | null
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

export type WaterBalanceSeriesResponse = {
  workflow_name: string
  field_id: number
  field_name?: string | null
  status: string
  ok: boolean
  warnings?: Array<WorkflowWarningRead>
  errors?: Array<WorkflowErrorRead>
  metadata?: {
  [key: string]: unknown
}
  data?: Array<WaterBalanceSeriesPoint>
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

export type WorkflowErrorRead = {
  message: string
  code?: string | null
  exception_type?: string | null
  details?: {
  [key: string]: unknown
}
  fatal?: boolean
}

export type WorkflowWarningRead = {
  message: string
  code?: string | null
  details?: {
  [key: string]: unknown
}
}
