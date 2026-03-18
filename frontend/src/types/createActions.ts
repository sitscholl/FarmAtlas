export type FieldCreatePayload = {
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
  humus_pct: number
  area_ha: number
  root_depth_cm: number
  p_allowable: number
}

export type IrrigationCreatePayload = {
  field_id: number
  date: string
  method: string
  amount: number
}

export type CreateActionField =
  | {
      id: keyof FieldCreatePayload | keyof IrrigationCreatePayload
      label: string
      type: 'text' | 'number' | 'date'
      placeholder?: string
      defaultValue?: string | number
      step?: string
      required?: boolean
    }
  | {
      id: keyof FieldCreatePayload | keyof IrrigationCreatePayload
      label: string
      type: 'select'
      optionsSource?: 'fields'
      options?: FieldOption[]
      defaultValue?: string | number
      required?: boolean
    }

export type CreateActionConfig = {
  id: 'field' | 'irrigation'
  label: string
  title: string
  submitLabel: string
  endpoint: string
  method?: 'post' | 'put'
  fields: CreateActionField[]
  buildPayload: (values: Record<string, string>) => FieldCreatePayload | IrrigationCreatePayload
}

export type FieldOption = {
  label: string
  value: string
}
