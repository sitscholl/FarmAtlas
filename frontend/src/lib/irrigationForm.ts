import { irrigationCreateAction, irrigationEditFields } from '../config/createActions'
import type { CreateActionConfig } from '../types/createActions'
import type { IrrigationRead } from '../types/generated/api'

export function buildIrrigationEditAction(
  event: IrrigationRead | null,
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
    fields: [...irrigationEditFields],
    buildPayload: (values) => ({
      field_id: Number(values.field_id),
      date: values.date,
      method: values.method.trim(),
      duration: Number(values.duration),
      amount: values.amount.trim() === '' ? null : Number(values.amount),
    }),
  }
}

export function buildIrrigationEditInitialValues(
  event: IrrigationRead | null,
): Record<string, string> | undefined {
  if (event === null) {
    return undefined
  }

  return {
    field_id: String(event.field_id),
    date: event.date,
    method: event.method,
    duration: String(event.duration),
    amount: String(event.amount),
  }
}
