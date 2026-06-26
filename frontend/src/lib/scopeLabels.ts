import type { FieldDetailRead } from '../types/generated/api'

export type ScopedRecord = {
  field_id?: number | null
  planting_id?: number | null
  section_id?: number | null
}

export type ScopeKind = 'field' | 'planting' | 'section' | 'unknown'

export type ScopeInfo = {
  kind: ScopeKind
  label: string
  fieldId: number | null
  fieldName: string
  fieldGroup: string
  plantingId: number | null
  plantingName: string
  sectionId: number | null
  sectionName: string
}

export type ScopeLookup = {
  fieldsById: Record<number, { name: string; group: string }>
  plantingsById: Record<number, { fieldId: number; fieldName: string; fieldGroup: string; name: string }>
  sectionsById: Record<
    number,
    {
      fieldId: number
      fieldName: string
      fieldGroup: string
      plantingId: number
      plantingName: string
      name: string
    }
  >
}

export function buildScopeLookup(fieldDetails: FieldDetailRead[]): ScopeLookup {
  const fieldsById: ScopeLookup['fieldsById'] = {}
  const plantingsById: ScopeLookup['plantingsById'] = {}
  const sectionsById: ScopeLookup['sectionsById'] = {}

  for (const fieldDetail of fieldDetails) {
    fieldsById[fieldDetail.field.id] = {
      name: fieldDetail.field.name,
      group: fieldDetail.field.group,
    }

    for (const planting of fieldDetail.plantings) {
      plantingsById[planting.id] = {
        fieldId: fieldDetail.field.id,
        fieldName: fieldDetail.field.name,
        fieldGroup: fieldDetail.field.group,
        name: planting.variety,
      }

      for (const section of planting.sections) {
        sectionsById[section.id] = {
          fieldId: fieldDetail.field.id,
          fieldName: fieldDetail.field.name,
          fieldGroup: fieldDetail.field.group,
          plantingId: planting.id,
          plantingName: planting.variety,
          name: section.name,
        }
      }
    }
  }

  return { fieldsById, plantingsById, sectionsById }
}

export function resolveScope(record: ScopedRecord, lookup: ScopeLookup): ScopeInfo {
  if (record.field_id !== null && record.field_id !== undefined) {
    const field = lookup.fieldsById[record.field_id]
    return {
      kind: 'field',
      label: field?.name ?? `Anlage #${record.field_id}`,
      fieldId: record.field_id,
      fieldName: field?.name ?? `#${record.field_id}`,
      fieldGroup: field?.group ?? 'n/a',
      plantingId: null,
      plantingName: '',
      sectionId: null,
      sectionName: '',
    }
  }

  if (record.planting_id !== null && record.planting_id !== undefined) {
    const planting = lookup.plantingsById[record.planting_id]
    return {
      kind: 'planting',
      label: planting === undefined ? `Pflanzung #${record.planting_id}` : planting.name,
      fieldId: planting?.fieldId ?? null,
      fieldName: planting?.fieldName ?? 'n/a',
      fieldGroup: planting?.fieldGroup ?? 'n/a',
      plantingId: record.planting_id,
      plantingName: planting?.name ?? `#${record.planting_id}`,
      sectionId: null,
      sectionName: '',
    }
  }

  if (record.section_id !== null && record.section_id !== undefined) {
    const section = lookup.sectionsById[record.section_id]
    return {
      kind: 'section',
      label: section === undefined ? `Abschnitt #${record.section_id}` : `${section.plantingName} | ${section.name}`,
      fieldId: section?.fieldId ?? null,
      fieldName: section?.fieldName ?? 'n/a',
      fieldGroup: section?.fieldGroup ?? 'n/a',
      plantingId: section?.plantingId ?? null,
      plantingName: section?.plantingName ?? '',
      sectionId: record.section_id,
      sectionName: section?.name ?? `#${record.section_id}`,
    }
  }

  return {
    kind: 'unknown',
    label: 'n/a',
    fieldId: null,
    fieldName: 'n/a',
    fieldGroup: 'n/a',
    plantingId: null,
    plantingName: '',
    sectionId: null,
    sectionName: '',
  }
}

export function getScopeKindLabel(kind: ScopeKind) {
  if (kind === 'field') {
    return 'Anlage'
  }
  if (kind === 'planting') {
    return 'Pflanzung'
  }
  if (kind === 'section') {
    return 'Abschnitt'
  }
  return 'n/a'
}
