import type { FieldCreate } from './generated/api'

export type FieldCreatePayload = FieldCreate

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
