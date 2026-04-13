import { varietyCreateAction } from '../config/createActions'
import type { CreateActionConfig } from '../types/createActions'
import type { VarietyRead, VarietyUpdate } from '../types/generated/api'

export function buildVarietyEditAction(
  variety: VarietyRead | null,
): CreateActionConfig | null {
  if (variety === null) {
    return null
  }

  return {
    ...varietyCreateAction,
    title: 'Sorte bearbeiten',
    submitLabel: 'Aenderungen speichern',
    endpoint: `/varieties/${variety.id}`,
    method: 'put',
    buildPayload: (values): VarietyUpdate =>
      varietyCreateAction.buildPayload(values) as VarietyUpdate,
  }
}

export function buildVarietyEditInitialValues(
  variety: VarietyRead | null,
): Record<string, string> | undefined {
  if (variety === null) {
    return undefined
  }

  return {
    name: variety.name,
    group: variety.group,
    nr_per_kg: String(variety.nr_per_kg ?? ''),
    kg_per_box: String(variety.kg_per_box ?? ''),
    slope: String(variety.slope ?? ''),
    intercept: String(variety.intercept ?? ''),
    specific_weight: String(variety.specific_weight ?? ''),
  }
}
