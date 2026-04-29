import type {
  FieldCreate,
  FieldUpdate,
  NutrientRequirementCreate,
  NutrientRequirementUpdate,
  PhenologyEventCreate,
  PlantingCreate,
  PlantingUpdate,
  SectionCreate,
  SectionUpdate,
  VarietyCreate,
  VarietyUpdate,
} from './generated/api'

export type FieldCreatePayload = FieldCreate
export type FieldUpdatePayload = FieldUpdate
export type NutrientRequirementCreatePayload = NutrientRequirementCreate
export type NutrientRequirementUpdatePayload = NutrientRequirementUpdate
export type PhenologyEventCreatePayload = PhenologyEventCreate
export type PlantingCreatePayload = PlantingCreate
export type PlantingUpdatePayload = PlantingUpdate
export type SectionCreatePayload = SectionCreate
export type SectionUpdatePayload = SectionUpdate
export type VarietyCreatePayload = VarietyCreate
export type VarietyUpdatePayload = VarietyUpdate

export type IrrigationCreatePayload = {
  field_id: number
  date: string
  method: string
  duration: number
  amount?: number | null
}

export type IrrigationBulkCreatePayload = {
  field_ids: number[]
  date: string
  method: string
  duration: number
  amount?: number | null
}

export type PhenologyBulkCreatePayload = {
  section_ids: number[]
  stage_code: string
  date: string
}

type ActionPayload =
  | FieldCreatePayload
  | FieldUpdatePayload
  | NutrientRequirementCreatePayload
  | NutrientRequirementUpdatePayload
  | PhenologyEventCreatePayload
  | PhenologyBulkCreatePayload
  | PlantingCreatePayload
  | PlantingUpdatePayload
  | SectionCreatePayload
  | SectionUpdatePayload
  | IrrigationCreatePayload
  | IrrigationBulkCreatePayload
  | VarietyCreatePayload
  | VarietyUpdatePayload

export type SecondaryCreateAction = {
  submitLabel: string
  endpoint: string
  method?: 'post' | 'put'
  buildPayload: (values: Record<string, string>) => ActionPayload
}

export type CreateActionField =
  | {
      id: string
      label: string
      type: 'text' | 'number' | 'date'
      placeholder?: string
      defaultValue?: string | number
      step?: string
      required?: boolean
    }
  | {
      id: string
      label: string
      type: 'select'
      optionsSource?: 'fields' | 'sections' | 'varieties' | 'varietiesOptional' | 'phenologicalStages'
      options?: readonly FieldOption[]
      defaultValue?: string | number
      required?: boolean
    }
  | {
      id: string
      label: string
      type: 'custom'
      renderer: 'groupedFieldSelector'
      selectionMode?: 'fields' | 'sections'
      required?: boolean
    }

export type CreateActionConfig = {
  id: 'field' | 'planting' | 'section' | 'irrigation' | 'phenology' | 'variety' | 'nutrient'
  label: string
  title: string
  submitLabel: string
  endpoint: string
  method?: 'post' | 'put'
  fields: CreateActionField[]
  buildPayload: (values: Record<string, string>) => ActionPayload
  secondaryAction?: SecondaryCreateAction
}

export type FieldOption = {
  label: string
  value: string
}
