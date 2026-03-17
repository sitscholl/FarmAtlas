import { type CreateActionConfig } from '../types/createActions'

export const createActions: CreateActionConfig[] = [
  {
    id: 'field',
    label: 'Anlage hinzufügen',
    title: 'Neue Anlage',
    submitLabel: 'Anlage anlegen',
    endpoint: '/fields',
    fields: [
      { id: 'name', label: 'Name', type: 'text', placeholder: 'Parzellenname', required: true },
      { id: 'reference_provider', label: 'Provider', type: 'text', defaultValue: 'sbr', required: true },
      { id: 'reference_station', label: 'Referenzstation', type: 'text', defaultValue: '103', required: true },
      { id: 'area_ha', label: 'Fläche (ha)', type: 'number', placeholder: '1', step: '0.1', required: true },
      { id: 'soil_type', label: 'Bodenart', type: 'text', placeholder: 'lehm', required: true },
      { id: 'humus_pct', label: 'Humusgehalt (%)', type: 'number', placeholder: '3', step: '0.1', required: true },
      { id: 'root_depth_cm', label: 'Wurzeltiefe (cm)', type: 'number', defaultValue: 30, step: '1', required: true },
      { id: 'p_allowable', label: 'p_allowable', type: 'number', defaultValue: 0.30, step: '0.01', required: true },
    ],
    buildPayload: (values) => ({
      name: values.name.trim(),
      reference_provider: values.reference_provider.trim(),
      reference_station: values.reference_station.trim(),
      soil_type: values.soil_type.trim(),
      humus_pct: Number(values.humus_pct),
      area_ha: Number(values.area_ha),
      root_depth_cm: Number(values.root_depth_cm),
      p_allowable: Number(values.p_allowable),
    }),
  },
  {
    id: 'irrigation',
    label: 'Bewässerung eintragen',
    title: 'Bewässerung eintragen',
    submitLabel: 'Bewässerung speichern',
    endpoint: '',
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
