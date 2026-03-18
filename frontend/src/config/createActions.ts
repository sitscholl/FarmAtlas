import { type CreateActionConfig } from '../types/createActions'

function toOptionalNumber(value: string) {
  return value.trim() === '' ? null : Number(value)
}

function toOptionalText(value: string) {
  const trimmed = value.trim()
  return trimmed === '' ? null : trimmed
}

function toOptionalBoolean(value: string) {
  if (value === '') {
    return null
  }

  return value === 'true'
}

export const fieldCreateAction: CreateActionConfig = {
  id: 'field',
  label: 'Anlage hinzufuegen',
  title: 'Neue Anlage',
  submitLabel: 'Anlage anlegen',
  endpoint: '/fields',
  method: 'post',
  fields: [
    { id: 'name', label: 'Name', type: 'text', placeholder: 'Parzellenname', required: true },
    { id: 'section', label: 'Abschnitt', type: 'text', placeholder: 'Nord', required: false },
    { id: 'variety', label: 'Sorte', type: 'text', placeholder: 'Gala', required: true },
    { id: 'area_ha', label: 'Flaeche (ha)', type: 'number', placeholder: '1', step: '0.1', required: true },
    { id: 'planting_year', label: 'Pflanzjahr', type: 'number', placeholder: '2018', step: '1', required: true },
    { id: 'tree_count', label: 'Baumzahl', type: 'number', placeholder: '250', step: '1', required: false },
    { id: 'tree_height', label: 'Baumhoehe (m)', type: 'number', placeholder: '3', step: '0.1', required: false },
    { id: 'row_distance', label: 'Reihenabstand (m)', type: 'number', placeholder: '3.5', step: '0.1', required: false },
    { id: 'tree_distance', label: 'Pflanzabstand (m)', type: 'number', placeholder: '1.2', step: '0.1', required: false },
    { id: 'running_metre', label: 'Laufmeter (m)', type: 'number', placeholder: '450', step: '0.1', required: false },
    {
      id: 'herbicide_free',
      label: 'Herbizidfrei',
      type: 'select',
      options: [
        { value: '', label: 'Keine Angabe' },
        { value: 'true', label: 'Ja' },
        { value: 'false', label: 'Nein' },
      ],
      required: false,
    },
    {
      id: 'active',
      label: 'Status',
      type: 'select',
      options: [
        { value: 'true', label: 'Aktiv' },
        { value: 'false', label: 'Inaktiv' },
      ],
      defaultValue: 'true',
      required: true,
    },
    { id: 'reference_provider', label: 'Provider', type: 'text', defaultValue: 'sbr', required: true },
    { id: 'reference_station', label: 'Referenzstation', type: 'text', defaultValue: '103', required: true },
    { id: 'soil_type', label: 'Bodenart', type: 'text', placeholder: 'lehm', required: true },
    { id: 'humus_pct', label: 'Humusgehalt (%)', type: 'number', placeholder: '3', step: '0.1', required: true },
    { id: 'root_depth_cm', label: 'Wurzeltiefe (cm)', type: 'number', defaultValue: 30, step: '1', required: true },
    { id: 'p_allowable', label: 'p_allowable', type: 'number', defaultValue: 0.30, step: '0.01', required: true },
  ],
  buildPayload: (values) => ({
    name: values.name.trim(),
    section: toOptionalText(values.section),
    variety: values.variety.trim(),
    planting_year: Number(values.planting_year),
    tree_count: toOptionalNumber(values.tree_count),
    tree_height: toOptionalNumber(values.tree_height),
    row_distance: toOptionalNumber(values.row_distance),
    tree_distance: toOptionalNumber(values.tree_distance),
    running_metre: toOptionalNumber(values.running_metre),
    herbicide_free: toOptionalBoolean(values.herbicide_free),
    active: values.active === 'true',
    reference_provider: values.reference_provider.trim(),
    reference_station: values.reference_station.trim(),
    soil_type: values.soil_type.trim(),
    humus_pct: Number(values.humus_pct),
    area_ha: Number(values.area_ha),
    root_depth_cm: Number(values.root_depth_cm),
    p_allowable: Number(values.p_allowable),
  }),
}

export const createActions: CreateActionConfig[] = [
  fieldCreateAction,
  {
    id: 'irrigation',
    label: 'Bewaesserung eintragen',
    title: 'Bewaesserung eintragen',
    submitLabel: 'Bewaesserung speichern',
    endpoint: '',
    method: 'post',
    fields: [
      { id: 'field_id', label: 'Anlage', type: 'select', optionsSource: 'fields', required: true },
      { id: 'date', label: 'Datum', type: 'date', required: true },
      { id: 'method', label: 'Methode', type: 'text', defaultValue: 'drip', required: true },
      { id: 'amount', label: 'Menge (mm)', type: 'number', defaultValue: 10, step: '0.1', required: true },
    ],
    buildPayload: (values) => ({
      field_id: Number(values.field_id),
      date: values.date,
      method: values.method.trim(),
      amount: Number(values.amount),
    }),
  },
]
