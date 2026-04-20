import { nutrientCreateAction } from '../config/createActions'
import type { CreateActionConfig } from '../types/createActions'
import type { NutrientRequirementRead, NutrientRequirementUpdate } from '../types/generated/api'

export function buildNutrientEditAction(
  nutrient: NutrientRequirementRead | null,
): CreateActionConfig | null {
  if (nutrient === null) {
    return null
  }

  return {
    ...nutrientCreateAction,
    title: 'Naehrstoffeintrag bearbeiten',
    submitLabel: 'Aenderungen speichern',
    endpoint: `/nutrients/${nutrient.id}`,
    method: 'put',
    buildPayload: (values): NutrientRequirementUpdate =>
      nutrientCreateAction.buildPayload(values) as NutrientRequirementUpdate,
  }
}

export function buildNutrientEditInitialValues(
  nutrient: NutrientRequirementRead | null,
): Record<string, string> | undefined {
  if (nutrient === null) {
    return undefined
  }

  return {
    variety: nutrient.variety ?? '',
    nutrient_code: nutrient.nutrient_code,
    requirement_per_kg_min: String(nutrient.requirement_per_kg_min),
    requirement_per_kg_mean: String(nutrient.requirement_per_kg_mean),
    requirement_per_kg_max: String(nutrient.requirement_per_kg_max),
  }
}
