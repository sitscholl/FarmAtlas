import { irrigationCreateAction } from '../config/createActions'
import type { CreateActionConfig } from '../types/createActions'
import type { IrrigationEvent } from '../types/irrigation'

export function buildIrrigationEditAction(
  event: IrrigationEvent | null,
): CreateActionConfig | null {
  if (event === null) {
    return null
  }

  return {
    ...irrigationCreateAction,
    title: 'Bewaesserung bearbeiten',
    submitLabel: 'Bewaesserung speichern',
    endpoint: `/irrigation/${event.id}`,
    method: 'put',
  }
}

export function buildIrrigationEditInitialValues(
  event: IrrigationEvent | null,
): Record<string, string> | undefined {
  if (event === null) {
    return undefined
  }

  return {
    field_id: String(event.field_id),
    date: event.date,
    method: event.method,
    amount: String(event.amount),
  }
}
