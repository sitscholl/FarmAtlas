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

function toSelectedFieldIds(value: string) {
  if (value.trim() === '') {
    return []
  }

  try {
    const parsed = JSON.parse(value) as unknown
    if (!Array.isArray(parsed)) {
      return []
    }

    return parsed
      .map((entry) => Number(entry))
      .filter((entry) => Number.isInteger(entry) && entry > 0)
  } catch {
    return []
  }
}

export const irrigationEditFields = [
  { id: 'field_id', label: 'Anlage', type: 'select', optionsSource: 'fields', required: true },
  { id: 'date', label: 'Datum', type: 'date', required: true },
  {
    id: 'method',
    label: 'Methode',
    type: 'select',
    options: [
      { value: 'drip', label: 'Tropfer' },
      { value: 'overhead', label: 'Oberkrone' },
    ],
    required: true,
  },
  { id: 'duration', label: 'Dauer (h)', type: 'number', defaultValue: 1, step: '0.5', required: true },
  { id: 'amount', label: 'Menge (mm)', type: 'number', step: '10', required: false },
] as const

export const irrigationCreateFields = [
  { id: 'field_ids', label: 'Anlagen', type: 'custom', renderer: 'groupedFieldSelector', required: true },
  { id: 'date', label: 'Datum', type: 'date', required: true },
  {
    id: 'method',
    label: 'Methode',
    type: 'select',
    options: [
      { value: 'drip', label: 'Tropfer' },
      { value: 'overhead', label: 'Oberkrone' },
    ],
    required: true,
  },
  { id: 'duration', label: 'Dauer (h)', type: 'number', defaultValue: 1, step: '0.5', required: true },
  { id: 'amount', label: 'Menge (mm)', type: 'number', step: '10', required: false },
] as const

export const fieldCreateAction: CreateActionConfig = {
  id: 'field',
  label: 'Anlage hinzufuegen',
  title: 'Neue Anlage',
  submitLabel: 'Anlage anlegen',
  endpoint: '/fields',
  method: 'post',
  fields: [
    { id: 'group', label: 'Gruppe', type: 'text', placeholder: 'Ostblock', required: true },
    { id: 'name', label: 'Name', type: 'text', placeholder: 'Parzellenname', required: true },
    { id: 'section', label: 'Abschnitt', type: 'text', placeholder: 'Nord', required: false },
    { id: 'variety', label: 'Sorte', type: 'select', optionsSource: 'varieties', required: true },
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
    { id: 'soil_type', label: 'Bodenart', type: 'text', placeholder: 'lehm', required: false },
    {
      id: 'soil_weight',
      label: 'Bodenschwere',
      type: 'select',
      options: [
        { value: '', label: 'Keine Angabe' },
        { value: 'sehr leicht', label: 'Sehr leicht' },
        { value: 'leicht', label: 'Leicht' },
        { value: 'mittel', label: 'Mittel' },
        { value: 'schwer', label: 'Schwer' },
      ],
      required: false,
    },
    { id: 'humus_pct', label: 'Humusgehalt (%)', type: 'number', placeholder: '3', step: '0.1', required: false },
    { id: 'effective_root_depth_cm', label: 'Effektive Wurzeltiefe (cm)', type: 'number', defaultValue: 30, step: '1', required: false },
    { id: 'p_allowable', label: 'Entziehbarer Wasseranteil (%)', type: 'number', defaultValue: 0.70, step: '0.01', required: false },
    { id: 'drip_distance', label: 'Tropferabstand (m)', type: 'number', defaultValue: 0.4, step: '0.01', required: false },
    { id: 'drip_discharge', label: 'Tropferleistung (l/h)', type: 'number', defaultValue: 2.1, step: '0.1', required: false },
    { id: 'tree_strip_width', label: 'Baumstreifenbreite (m)', type: 'number', defaultValue: 1, step: '0.01', required: false },
  ],
  buildPayload: (values) => ({
    group: values.group.trim(),
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
    soil_type: toOptionalText(values.soil_type),
    soil_weight: toOptionalText(values.soil_weight),
    humus_pct: toOptionalNumber(values.humus_pct),
    area_ha: Number(values.area_ha),
    effective_root_depth_cm: toOptionalNumber(values.effective_root_depth_cm),
    p_allowable: toOptionalNumber(values.p_allowable),
    drip_distance: toOptionalNumber(values.drip_distance),
    drip_discharge: toOptionalNumber(values.drip_discharge),
    tree_strip_width: toOptionalNumber(values.tree_strip_width),
  }),
}

export const varietyCreateAction: CreateActionConfig = {
  id: 'variety',
  label: 'Sorte hinzufuegen',
  title: 'Neue Sorte',
  submitLabel: 'Sorte anlegen',
  endpoint: '/varieties',
  method: 'post',
  fields: [
    { id: 'name', label: 'Name', type: 'text', placeholder: 'Gala', required: true },
    { id: 'group', label: 'Gruppe', type: 'text', placeholder: 'Apfel', required: true },
    { id: 'nr_per_kg', label: 'N pro kg', type: 'number', placeholder: '0.03', step: '0.001', required: false },
    { id: 'kg_per_box', label: 'kg pro Kiste', type: 'number', placeholder: '12', step: '0.1', required: false },
    { id: 'slope', label: 'Slope', type: 'number', placeholder: '1', step: '0.001', required: false },
    { id: 'intercept', label: 'Intercept', type: 'number', placeholder: '0', step: '0.001', required: false },
    { id: 'specific_weight', label: 'Spez. Gewicht', type: 'number', placeholder: '0.8', step: '0.001', required: false },
  ],
  buildPayload: (values) => ({
    name: values.name.trim(),
    group: values.group.trim(),
    nr_per_kg: toOptionalNumber(values.nr_per_kg),
    kg_per_box: toOptionalNumber(values.kg_per_box),
    slope: toOptionalNumber(values.slope),
    intercept: toOptionalNumber(values.intercept),
    specific_weight: toOptionalNumber(values.specific_weight),
  }),
}

export const irrigationCreateAction: CreateActionConfig = {
  id: 'irrigation',
  label: 'Bewaesserung eintragen',
  title: 'Bewaesserung eintragen',
  submitLabel: 'Bewaesserung speichern',
  endpoint: '/irrigation/bulk',
  method: 'post',
  fields: [...irrigationCreateFields],
  buildPayload: (values) => ({
    field_ids: toSelectedFieldIds(values.field_ids ?? ''),
    date: values.date,
    method: values.method.trim(),
    duration: Number(values.duration),
    amount: values.amount.trim() === '' ? null : Number(values.amount),
  }),
}

export const createActions: CreateActionConfig[] = [fieldCreateAction, varietyCreateAction, irrigationCreateAction]
