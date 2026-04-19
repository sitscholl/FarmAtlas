import {
  fieldCreateAction,
  plantingCreateAction,
  sectionCreateAction,
  squareMetresToHectares,
} from '../config/createActions'
import type { CreateActionConfig } from '../types/createActions'
import type {
  FieldRead,
  PlantingDetailRead,
  PlantingRead,
  SectionRead,
} from '../types/generated/api'

function boolToString(value: boolean | null | undefined) {
  if (value === null || value === undefined) {
    return ''
  }
  return String(value)
}

export function buildFieldEditAction(field: FieldRead | null): CreateActionConfig | null {
  if (field === null) {
    return null
  }

  return {
    ...fieldCreateAction,
    title: 'Anlage bearbeiten',
    submitLabel: 'Aenderungen speichern',
    endpoint: `/fields/${field.id}`,
    method: 'put',
  }
}

export function buildFieldEditInitialValues(
  field: FieldRead | null,
): Record<string, string> | undefined {
  if (field === null) {
    return undefined
  }

  return {
    group: field.group,
    name: field.name,
    reference_provider: field.reference_provider,
    reference_station: field.reference_station,
    elevation: String(field.elevation),
    soil_type: field.soil_type ?? '',
    soil_weight: field.soil_weight ?? '',
    humus_pct: String(field.humus_pct ?? ''),
    effective_root_depth_cm: String(field.effective_root_depth_cm ?? ''),
    p_allowable: String(field.p_allowable ?? ''),
    drip_distance: String(field.drip_distance ?? ''),
    drip_discharge: String(field.drip_discharge ?? ''),
    tree_strip_width: String(field.tree_strip_width ?? ''),
    valve_open: String(field.valve_open),
  }
}

export function buildPlantingCreateAction(fieldId: number): CreateActionConfig {
  return {
    ...plantingCreateAction,
    fields: plantingCreateAction.fields.filter((field) => field.id !== 'field_id'),
    buildPayload: (values) => ({
      field_id: fieldId,
      variety: values.variety.trim(),
      valid_from: values.valid_from,
      valid_to: values.valid_to.trim() === '' ? null : values.valid_to,
    }),
  }
}

export function buildPlantingEditAction(planting: PlantingRead | PlantingDetailRead | null): CreateActionConfig | null {
  if (planting === null) {
    return null
  }

  return {
    ...plantingCreateAction,
    title: 'Pflanzung bearbeiten',
    submitLabel: 'Aenderungen speichern',
    endpoint: `/plantings/${planting.id}`,
    method: 'put',
    fields: plantingCreateAction.fields.filter((field) => field.id !== 'field_id'),
    buildPayload: (values) => ({
      variety: values.variety.trim(),
      valid_from: values.valid_from,
      valid_to: values.valid_to.trim() === '' ? null : values.valid_to,
    }),
  }
}

export function buildPlantingEditInitialValues(
  planting: PlantingRead | PlantingDetailRead | null,
): Record<string, string> | undefined {
  if (planting === null) {
    return undefined
  }

  return {
    variety: planting.variety,
    valid_from: planting.valid_from,
    valid_to: planting.valid_to ?? '',
  }
}

export function buildSectionCreateAction(plantingId: number): CreateActionConfig {
  return {
    ...sectionCreateAction,
    buildPayload: (values) => ({
      planting_id: plantingId,
      name: values.name.trim(),
      planting_year: Number(values.planting_year),
      area: Number(values.area_ha) * 10000,
      tree_count: values.tree_count.trim() === '' ? null : Number(values.tree_count),
      tree_height: values.tree_height.trim() === '' ? null : Number(values.tree_height),
      row_distance: values.row_distance.trim() === '' ? null : Number(values.row_distance),
      tree_distance: values.tree_distance.trim() === '' ? null : Number(values.tree_distance),
      running_metre: values.running_metre.trim() === '' ? null : Number(values.running_metre),
      herbicide_free: values.herbicide_free === '' ? null : values.herbicide_free === 'true',
      valid_from: values.valid_from,
      valid_to: values.valid_to.trim() === '' ? null : values.valid_to,
    }),
  }
}

export function buildSectionEditAction(section: SectionRead | null): CreateActionConfig | null {
  if (section === null) {
    return null
  }

  return {
    ...sectionCreateAction,
    title: 'Abschnitt bearbeiten',
    submitLabel: 'Aenderungen speichern',
    endpoint: `/sections/${section.id}`,
    method: 'put',
    buildPayload: (values) => ({
      name: values.name.trim(),
      planting_year: Number(values.planting_year),
      area: Number(values.area_ha) * 10000,
      tree_count: values.tree_count.trim() === '' ? null : Number(values.tree_count),
      tree_height: values.tree_height.trim() === '' ? null : Number(values.tree_height),
      row_distance: values.row_distance.trim() === '' ? null : Number(values.row_distance),
      tree_distance: values.tree_distance.trim() === '' ? null : Number(values.tree_distance),
      running_metre: values.running_metre.trim() === '' ? null : Number(values.running_metre),
      herbicide_free: values.herbicide_free === '' ? null : values.herbicide_free === 'true',
      valid_from: values.valid_from,
      valid_to: values.valid_to.trim() === '' ? null : values.valid_to,
    }),
  }
}

export function buildSectionEditInitialValues(
  section: SectionRead | null,
): Record<string, string> | undefined {
  if (section === null) {
    return undefined
  }

  return {
    name: section.name,
    planting_year: String(section.planting_year),
    area_ha: squareMetresToHectares(section.area),
    tree_count: String(section.tree_count ?? ''),
    tree_height: String(section.tree_height ?? ''),
    row_distance: String(section.row_distance ?? ''),
    tree_distance: String(section.tree_distance ?? ''),
    running_metre: String(section.running_metre ?? ''),
    herbicide_free: boolToString(section.herbicide_free),
    valid_from: section.valid_from,
    valid_to: section.valid_to ?? '',
  }
}
