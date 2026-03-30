import { fieldCreateAction } from '../config/createActions'
import type { CreateActionConfig } from '../types/createActions'
import type { FieldCreate, FieldOverview, FieldUpdate } from '../types/generated/api'

export function buildFieldEditAction(field: FieldOverview | null): CreateActionConfig | null {
  if (field === null) {
    return null
  }

  const effectiveFromField = {
    id: 'effective_from' as const,
    label: 'Gueltig ab',
    type: 'date' as const,
    required: true,
  }

  return {
    ...fieldCreateAction,
    title: 'Anlage bearbeiten',
    submitLabel: 'Version ersetzen',
    endpoint: `/fields/${field.id}`,
    method: 'put',
    fields: [effectiveFromField, ...fieldCreateAction.fields],
    buildPayload: (values): FieldUpdate => ({
      ...(fieldCreateAction.buildPayload(values) as FieldCreate),
      effective_from: values.effective_from,
    }),
  }
}

export function buildFieldEditInitialValues(
  field: FieldOverview | null,
): Record<string, string> | undefined {
  if (field === null) {
    return undefined
  }

  return {
    effective_from: new Date().toISOString().slice(0, 10),
    unique_name: field.unique_name,
    group: field.group,
    name: field.name,
    section: field.section ?? '',
    variety: field.variety,
    planting_year: String(field.planting_year),
    tree_count: String(field.tree_count ?? ''),
    tree_height: String(field.tree_height ?? ''),
    row_distance: String(field.row_distance ?? ''),
    tree_distance: String(field.tree_distance ?? ''),
    running_metre: String(field.running_metre ?? ''),
    herbicide_free: field.herbicide_free === null ? '' : String(field.herbicide_free),
    active: String(field.active),
    reference_provider: field.reference_provider,
    reference_station: field.reference_station,
    area_ha: String(field.area_ha ?? ''),
    soil_type: field.soil_type ?? '',
    soil_weight: field.soil_weight ?? '',
    humus_pct: String(field.humus_pct ?? ''),
    effective_root_depth_cm: String(field.effective_root_depth_cm ?? ''),
    p_allowable: String(field.p_allowable ?? ''),
  }
}
