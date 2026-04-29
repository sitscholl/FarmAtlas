import { phenologyCreateAction } from '../config/createActions'
import type { CreateActionConfig } from '../types/createActions'
import type { PhenologyEventRead } from '../types/generated/api'

export function buildPhenologyEditAction(
  event: PhenologyEventRead | null,
): CreateActionConfig | null {
  if (event === null) {
    return null
  }

  return {
    ...phenologyCreateAction,
    title: 'Phaenologie bearbeiten',
    submitLabel: 'Phaenologie speichern',
    endpoint: `/phenology-events/${event.id}`,
    method: 'put',
    fields: [
      {
        id: 'section_id',
        label: 'Abschnitt',
        type: 'select',
        optionsSource: 'sections',
        required: true,
      },
      {
        id: 'stage_code',
        label: 'Stadium',
        type: 'select',
        optionsSource: 'phenologicalStages',
        required: true,
      },
      { id: 'date', label: 'Datum', type: 'date', required: true },
    ],
    buildPayload: (values) => ({
      section_id: Number(values.section_id),
      stage_code: values.stage_code.trim(),
      date: values.date,
    }),
  }
}

export function buildPhenologyEditInitialValues(
  event: PhenologyEventRead | null,
): Record<string, string> | undefined {
  if (event === null) {
    return undefined
  }

  return {
    section_id: String(event.section_id),
    stage_code: event.stage_code,
    date: event.date,
  }
}
