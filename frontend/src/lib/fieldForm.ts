import { fieldCreateAction } from '../config/createActions'
import type { CreateActionConfig } from '../types/createActions'
import type { FieldOverview } from '../types/field'

export function buildFieldEditAction(field: FieldOverview | null): CreateActionConfig | null {
  if (field === null) {
    return null
  }

  return {
    ...fieldCreateAction,
    title: 'Anlage bearbeiten',
    submitLabel: 'Anlage speichern',
    endpoint: `/fields/${field.id}`,
    method: 'put',
  }
}

export function buildFieldEditInitialValues(
  field: FieldOverview | null,
): Record<string, string> | undefined {
  if (field === null) {
    return undefined
  }

  return {
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
    soil_type: field.soil_type,
    soil_weight: field.soil_weight ?? '',
    humus_pct: String(field.humus_pct),
    effective_root_depth_cm: String(field.effective_root_depth_cm),
    p_allowable: String(field.p_allowable),
  }
}
