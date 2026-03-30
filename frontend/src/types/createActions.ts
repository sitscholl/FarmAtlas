import type { FieldCreate, FieldUpdate, VarietyCreate } from './generated/api'

export type FieldCreatePayload = FieldCreate
export type FieldUpdatePayload = FieldUpdate
export type VarietyCreatePayload = VarietyCreate

export type IrrigationCreatePayload = {
  field_id: number
  date: string
  method: string
  amount: number
}

type ActionFieldId =
  | keyof FieldCreatePayload
  | keyof FieldUpdatePayload
  | keyof IrrigationCreatePayload
  | keyof VarietyCreatePayload

type ActionPayload =
  | FieldCreatePayload
  | FieldUpdatePayload
  | IrrigationCreatePayload
  | VarietyCreatePayload

export type CreateActionField =
  | {
      id: ActionFieldId
      label: string
      type: 'text' | 'number' | 'date'
      placeholder?: string
      defaultValue?: string | number
      step?: string
      required?: boolean
    }
  | {
      id: ActionFieldId
      label: string
      type: 'select'
      optionsSource?: 'fields' | 'varieties'
      options?: FieldOption[]
      defaultValue?: string | number
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
}

export type FieldOption = {
  label: string
  value: string
}
