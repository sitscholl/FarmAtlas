import type {
  FieldCreate,
  FieldReplant,
  FieldUpdate,
  VarietyCreate,
  VarietyUpdate,
} from './generated/api'

export type FieldCreatePayload = FieldCreate
export type FieldUpdatePayload = FieldUpdate
export type FieldReplantPayload = FieldReplant
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

type ActionPayload =
  | FieldCreatePayload
  | FieldUpdatePayload
  | FieldReplantPayload
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
      optionsSource?: 'fields' | 'varieties'
      options?: readonly FieldOption[]
      defaultValue?: string | number
      required?: boolean
    }
  | {
      id: string
      label: string
      type: 'custom'
      renderer: 'groupedFieldSelector'
      required?: boolean
    }

export type CreateActionConfig = {
  id: 'field' | 'irrigation' | 'variety'
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
