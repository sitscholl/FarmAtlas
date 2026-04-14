import type { FieldRead } from './generated/api'

export type GroupedFieldSection = {
  section?: string | null
  field: FieldRead
}

export type GroupedFieldVariety = {
  variety: string
  field_ids: number[]
  sections: GroupedFieldSection[]
}

export type GroupedFieldNode = {
  name: string
  active: boolean
  field_ids: number[]
  varieties: GroupedFieldVariety[]
}

export type GroupedFieldResponse = {
  fields: GroupedFieldNode[]
}
